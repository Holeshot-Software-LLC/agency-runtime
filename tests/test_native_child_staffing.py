"""Adversarial contracts for inference-owned native-child staffing."""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import replace
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from typing import Any

import pytest

from agency_runtime.core import native_child_staffing as staffing
from agency_runtime.core.config import (
    AgencyConfig,
    AgentActivationConfig,
    CanaryConfig,
    HarnessInferenceConfig,
    InferenceConfig,
    InferenceProfile,
    JudgeConfig,
    OllamaConfig,
    ProviderEntry,
)
from agency_runtime.core.native_child_decision import (
    canonical_native_child_provider_receipt_digest,
    project_native_child_staffing_decision,
)
from agency_runtime.core.native_child_install_identity import NativeChildInstallIdentity
from agency_runtime.core.native_child_prompt_delivery import parse_inference_team_delivery
from agency_runtime.core.routing_snapshot import RoutingSnapshot
from agency_runtime.core.store import maintenance
from agency_runtime.core.store.sqlite import Store


@pytest.fixture(autouse=True)
def _deterministic_staffing_decision_ids(monkeypatch: pytest.MonkeyPatch) -> None:
    counter = iter(range(1, 100))
    monkeypatch.setattr(staffing, "_decision_id", lambda: f"route-{next(counter)}")


def _digest(value: str) -> str:
    return sha256(value.encode()).hexdigest()


def _agent(
    slug: str,
    prompt: str,
    *,
    requires: tuple[str, ...] = (),
    audit_status: str = "approved",
) -> dict[str, Any]:
    return {
        "slug": slug,
        "version": f"revision-{slug}",
        "hash": _digest(prompt),
        "audit_status": audit_status,
        "routing_contract_valid": True,
        "supported_execution_hosts": ["claude"],
        "requires": list(requires),
        "conflicts_with": [],
        "required_tools": [],
        "authority": "advise",
        "context_mode": "direct_safe",
    }


class _Store:
    def __init__(
        self,
        catalog: list[dict[str, Any]],
        prompts: dict[str, str],
    ) -> None:
        self.catalog = catalog
        self.prompts = prompts
        self.prompt_reads: list[str] = []
        self.decisions: list[dict[str, Any]] = []
        self.captured_assignments: list[dict[str, Any]] = []
        self.decision_ids: set[str] = set()
        self.roster_generation = 7
        self.close_before_record = False
        self.disable_before_record = False
        self.disabled_agents: frozenset[str] = frozenset()
        self.run: dict[str, Any] | None = {
            "trace_id": "parent-trace",
            "session_id": "parent-session",
            "host": "claude",
            "status": "active",
        }

    def get_run(self, trace_id: str) -> dict[str, Any] | None:
        if self.run is None or self.run.get("trace_id") != trace_id:
            return None
        return dict(self.run)

    def record_native_child_captured_assignment(self, **kwargs: Any) -> bool:
        self.captured_assignments.append(dict(kwargs))
        return True

    def get_routing_roster_snapshot(self, **_kwargs: Any) -> dict[str, Any]:
        return {"generation": self.roster_generation, "catalog": self.catalog}

    def get_versioned_specialist_prompt(
        self,
        slug: str,
        version: str,
        content_hash: str,
        **_kwargs: Any,
    ) -> dict[str, Any] | None:
        self.prompt_reads.append(slug)
        body = self.prompts.get(slug)
        if body is None:
            return None
        return {
            "slug": slug,
            "version": version,
            "hash": content_hash,
            "prompt_body": body,
            "prompt_truncated": False,
        }

    def record_routing_decision(self, **values: Any) -> str:
        if self.close_before_record and self.run is not None:
            self.run["status"] = "completed"
        if values.get("require_open_run") is True and (
            self.run is None or self.run.get("status") not in {"active", "evidence_only"}
        ):
            raise ValueError("trace_id belongs to a terminal turn")
        expected_generation = values.get("expected_roster_generation")
        if expected_generation is not None and expected_generation != self.roster_generation:
            raise ValueError("roster changed before routing decision persistence")
        if self.disable_before_record:
            self.disabled_agents = frozenset({*self.disabled_agents, "alpha-reviewer"})
        expected_disabled = values.get("expected_disabled_agents")
        if expected_disabled is not None and tuple(expected_disabled) != tuple(
            sorted(self.disabled_agents)
        ):
            raise ValueError("activation policy changed before routing decision persistence")
        final_delivery_validator = values.get("final_delivery_validator")
        if final_delivery_validator is not None and final_delivery_validator() is not True:
            raise ValueError("final native-child delivery validation failed")
        decision_id = str(values.get("decision_id") or f"route-{len(self.decisions) + 1}")
        if decision_id in self.decision_ids:
            raise RuntimeError("routing decision ID collision")
        self.decision_ids.add(decision_id)
        self.decisions.append(values)
        return decision_id

    def get_native_child_staffing_decision(
        self,
        decision_id: str,
    ) -> dict[str, Any] | None:
        values = next(
            (
                item
                for index, item in enumerate(self.decisions, start=1)
                if str(item.get("decision_id") or f"route-{index}") == decision_id
            ),
            None,
        )
        if values is None:
            return None
        decision = values["decision"]
        expected = project_native_child_staffing_decision(decision.get("native_child_delivery"))
        expected_ids = (
            [] if expected is None else [card["specialist_slug"] for card in expected["cards"]]
        )
        if (
            expected is None
            or decision.get("status") != "applied"
            or decision.get("source") != "native_child_inference"
            or decision.get("selected_ids") != expected_ids
            or decision.get("semantic_ids") != expected_ids
            or decision.get("companion_ids") != []
        ):
            return None
        return {"decision_id": decision_id, **expected}


def _install() -> NativeChildInstallIdentity:
    runtime_digest = _digest("runtime")
    return NativeChildInstallIdentity(
        host="claude",
        plugin_version="0.1.0+claude.test",
        install_id="install-1",
        bundle_digest=_digest("bundle"),
        running_runtime_digest=runtime_digest,
        candidate_digest=runtime_digest,
    )


def _attempt(status: str = "applied", *, name: str = "primary") -> dict[str, str]:
    return {
        "provider_name": name,
        "provider_type": "litellm",
        "requested_model": "task-general",
        "model_group": "production-router",
        "actual_model": "gpt-5.6",
        "model_receipt_source": "litellm",
        "status": status,
        "reason": "" if status == "applied" else "provider_call_failed",
    }


def _judge_result(selected: object) -> dict[str, Any]:
    return {
        "selected_ids": selected,
        "confidence": 0.97,
        "latency_ms": 9,
        "status": "applied",
        "inference_mode": "inferred",
        "provider_name": "primary",
        "candidate_count": 2,
        "top_score": 0.0,
        "provider_attempts": [_attempt("failed", name="first"), _attempt()],
    }


def _invoke(
    monkeypatch: pytest.MonkeyPatch,
    store: _Store,
    judge_result: dict[str, Any] | Callable[..., dict[str, Any]],
    **overrides: Any,
) -> staffing.NativeChildStaffingResult:
    judge = judge_result if callable(judge_result) else (lambda *_args, **_kwargs: judge_result)
    monkeypatch.setattr(staffing, "query_judge", judge)
    monkeypatch.setattr(
        staffing,
        "_utc_now",
        lambda: datetime(2026, 8, 12, 12, 0, tzinfo=timezone.utc),
    )
    monkeypatch.setattr(staffing, "_nonce", lambda: "nonce-one")
    values: dict[str, Any] = {
        "host": "claude",
        "task": "Review the exact authentication boundary.",
        "parent_session_id": "parent-session",
        "parent_trace_id": "parent-trace",
        "launch_id": "tool-use-1",
        "binding_kind": "launch_id",
        "binding_id": "tool-use-1",
        "install_identity": _install(),
        "install_identity_reader": lambda _host: _install(),
        "config": AgencyConfig(ollama=OllamaConfig(enabled=False)),
        "platform": "windows",
        "available_tools": (),
        "capability_status": "native-contract-verified",
    }
    values.update(overrides)
    return staffing.staff_native_child(store, **values)


def test_inference_order_is_preserved_and_only_hard_eligible_catalog_reaches_judge(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    prompts = {
        "alpha-reviewer": "Alpha exact specialist prompt.",
        "beta-reviewer": "Beta exact specialist prompt.",
        "pending-reviewer": "Must remain ineligible.",
    }
    catalog = [
        _agent("alpha-reviewer", prompts["alpha-reviewer"]),
        _agent("pending-reviewer", prompts["pending-reviewer"], audit_status="pending"),
        _agent("beta-reviewer", prompts["beta-reviewer"]),
    ]
    store = _Store(catalog, prompts)
    observed_catalog: list[list[str]] = []
    observed_candidate_scopes: list[str] = []

    def judge(_task: str, candidates: list[dict[str, Any]], **kwargs: Any) -> dict[str, Any]:
        observed_catalog.append([str(item["slug"]) for item in candidates])
        observed_candidate_scopes.append(str(kwargs.get("candidate_scope") or ""))
        return _judge_result(["beta-reviewer", "alpha-reviewer"])

    monkeypatch.setattr(staffing, "query_judge", judge)
    monkeypatch.setattr(
        staffing,
        "_utc_now",
        lambda: datetime(2026, 8, 12, 12, 0, tzinfo=timezone.utc),
    )
    monkeypatch.setattr(staffing, "_nonce", lambda: "nonce-one")

    result = staffing.staff_native_child(
        store,
        host="claude",
        task="Review the exact authentication boundary.",
        parent_session_id="parent-session",
        parent_trace_id="parent-trace",
        launch_id="tool-use-1",
        binding_kind="launch_id",
        binding_id="tool-use-1",
        install_identity=_install(),
        install_identity_reader=lambda _host: _install(),
        config=AgencyConfig(ollama=OllamaConfig(enabled=False)),
        platform="windows",
        available_tools=(),
        capability_status="native-contract-verified",
    )

    assert result.staffed is True
    assert result.status == "staffed"
    assert result.selected_ids == ("beta-reviewer", "alpha-reviewer")
    assert observed_catalog == [["alpha-reviewer", "beta-reviewer"]]
    assert observed_candidate_scopes == ["complete"]
    assert store.prompt_reads == ["beta-reviewer", "alpha-reviewer"]
    assert result.rewritten_task == (
        "Review the exact authentication boundary." + result.context_segment
    )
    parsed = parse_inference_team_delivery(result.rewritten_task)
    assert parsed is not None
    assert parsed.decision_id == "route-1"
    assert parsed.launch_id == "tool-use-1"
    assert parsed.binding_kind == "launch_id"
    assert parsed.binding_id == "tool-use-1"
    assert [card.specialist_slug for card in parsed.cards] == [
        "beta-reviewer",
        "alpha-reviewer",
    ]
    assert result.native_child_delivery == project_native_child_staffing_decision(
        result.native_child_delivery
    )
    assert result.provider_receipt_digest == canonical_native_child_provider_receipt_digest(
        result.provider_attempts
    )
    [persisted] = store.decisions
    assert persisted["decision"]["selected_ids"] == ["beta-reviewer", "alpha-reviewer"]
    assert persisted["decision"]["companion_ids"] == []
    assert persisted["decision"]["native_child_reason"] == "applied"
    assert persisted["decision"]["native_child_delivery"] == result.native_child_delivery
    stored = store.get_native_child_staffing_decision("route-1")
    assert stored is not None
    assert stored["cards"] == result.native_child_delivery["cards"]


def test_prefixed_store_hash_hydrates_to_canonical_delivery_identity(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    prompt = "Exact specialist prompt with a prefixed Store identity."
    prompt_digest = _digest(prompt)
    agent = _agent("alpha-reviewer", prompt)
    agent["hash"] = f"sha256:{prompt_digest}"
    store = _Store([agent], {"alpha-reviewer": prompt})
    observed_hashes: list[str] = []
    prompt_reader = store.get_versioned_specialist_prompt

    def read_prompt(slug: str, version: str, content_hash: str, **kwargs: Any) -> object:
        observed_hashes.append(content_hash)
        return prompt_reader(slug, version, content_hash, **kwargs)

    monkeypatch.setattr(store, "get_versioned_specialist_prompt", read_prompt)

    result = _invoke(monkeypatch, store, _judge_result(["alpha-reviewer"]))

    assert result.staffed is True
    assert store.prompt_reads == ["alpha-reviewer"]
    assert observed_hashes == [f"sha256:{prompt_digest}"]
    parsed = parse_inference_team_delivery(result.rewritten_task)
    assert parsed is not None
    assert parsed.cards[0].specialist_prompt_hash == prompt_digest
    assert result.native_child_delivery["cards"][0]["specialist_prompt_hash"] == prompt_digest
    assert result.native_child_delivery == project_native_child_staffing_decision(
        result.native_child_delivery
    )


def test_canary_pin_constrains_initial_and_abstention_repair_calls(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    prompt = "Alpha exact specialist prompt."
    store = _Store([_agent("alpha-reviewer", prompt)], {"alpha-reviewer": prompt})
    observed: list[tuple[tuple[str, ...], float]] = []

    def judge(task: str, _catalog: list[dict[str, Any]], **kwargs: Any) -> dict[str, Any]:
        observed.append(
            (
                tuple(provider.name for provider in kwargs["config"].providers),
                kwargs["config"].judge.timeout,
            )
        )
        selected = ["alpha-reviewer"] if task.startswith("A previous evaluation") else []
        result = _judge_result(selected)
        result["provider_name"] = "codex-subscription"
        result["provider_attempts"] = [_attempt(name="codex-subscription")]
        return result

    monkeypatch.setenv("AGENCY_CANARY_MODE", "1")
    monkeypatch.setenv("AGENCY_CANARY_CHILD_JUDGE_PROVIDER", "codex-subscription")
    config = AgencyConfig(
        providers=(
            ProviderEntry(
                name="claude-subscription",
                type="cli",
                transport="claude",
            ),
            ProviderEntry(
                name="codex-subscription",
                type="cli",
                transport="codex",
                timeout=120.0,
            ),
        ),
        judge=JudgeConfig(timeout=60.0),
        canary=CanaryConfig(
            child_judge_provider_by_host=(("claude", "codex-subscription"),),
        ),
        ollama=OllamaConfig(enabled=False),
    )
    result = _invoke(
        monkeypatch,
        store,
        judge,
        config=config,
    )

    assert result.staffed is True
    assert observed == [
        (("codex-subscription",), 120.0),
        (("codex-subscription",), 120.0),
    ]
    assert config.judge.timeout == 60.0
    assert store.decisions[-1]["decision"]["requested_provider"] == "codex-subscription"
    assert store.decisions[-1]["decision"]["provider"] == "codex-subscription"


@pytest.mark.parametrize(
    ("host", "expected_judge_timeout"),
    (("openclaw", 120.0), ("hermes", 15.0)),
)
def test_non_canary_native_child_uses_host_scoped_workforce_profile_without_provider_fallback(
    monkeypatch: pytest.MonkeyPatch,
    host: str,
    expected_judge_timeout: float,
) -> None:
    prompt = "Alpha exact specialist prompt."
    agent = _agent("alpha-reviewer", prompt)
    agent["supported_execution_hosts"] = [host]
    store = _Store([agent], {"alpha-reviewer": prompt})
    assert store.run is not None
    store.run["host"] = host
    observed: list[tuple[tuple[tuple[str, str, str], ...], float]] = []

    def judge(task: str, _catalog: list[dict[str, Any]], **kwargs: Any) -> dict[str, Any]:
        observed.append(
            (
                tuple(
                    (provider.name, provider.type, provider.model)
                    for provider in kwargs["config"].providers
                ),
                kwargs["config"].judge.timeout,
            )
        )
        selected = ["alpha-reviewer"] if task.startswith("A previous evaluation") else []
        result = _judge_result(selected)
        result["provider_name"] = "linux-task-agency-router"
        attempt = _attempt(name="linux-task-agency-router")
        attempt["requested_model"] = "task-agency-router"
        attempt["model_group"] = "task-agency-router"
        result["provider_attempts"] = [attempt]
        return result

    config = AgencyConfig(
        providers=(ProviderEntry(name="legacy-chain", type="cli", transport="codex"),),
        inference=InferenceConfig(
            profiles={
                "linux-task-agency-router": InferenceProfile(
                    name="linux-task-agency-router",
                    adapter="litellm",
                    model="task-agency-router",
                    base_url="http://127.0.0.1:4000/v1",
                    api_key="bounded-test-key",
                    timeout_ms=120_000,
                )
            },
            harnesses={
                host: HarnessInferenceConfig(
                    default_profile="linux-task-agency-router",
                )
            },
        ),
        ollama=OllamaConfig(enabled=False),
    )
    monkeypatch.delenv("AGENCY_CANARY_MODE", raising=False)
    host_install = replace(_install(), host=host)

    result = _invoke(
        monkeypatch,
        store,
        judge,
        config=config,
        host=host,
        install_identity=host_install,
        install_identity_reader=lambda _host: host_install,
    )

    expected = (
        (("linux-task-agency-router", "litellm", "task-agency-router"),),
        expected_judge_timeout,
    )
    assert result.staffed is True
    assert observed == [expected, expected]
    assert config.providers[0].name == "legacy-chain"
    assert config.judge.timeout == 15.0


def test_canary_pin_projection_mismatch_fails_before_judge(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    prompt = "Alpha exact specialist prompt."
    store = _Store([_agent("alpha-reviewer", prompt)], {"alpha-reviewer": prompt})
    invoked = False

    def judge(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
        nonlocal invoked
        invoked = True
        return _judge_result(["alpha-reviewer"])

    monkeypatch.setenv("AGENCY_CANARY_MODE", "1")
    monkeypatch.setenv("AGENCY_CANARY_CHILD_JUDGE_PROVIDER", "claude-subscription")
    result = _invoke(
        monkeypatch,
        store,
        judge,
        config=AgencyConfig(
            providers=(ProviderEntry(name="codex-subscription", type="cli", transport="codex"),),
            canary=CanaryConfig(
                child_judge_provider_by_host=(("claude", "codex-subscription"),),
            ),
            ollama=OllamaConfig(enabled=False),
        ),
    )

    assert result.staffed is False
    assert result.reason_code == "native_child_canary_provider_invalid"
    assert invoked is False


def test_zcode_canary_profile_constrains_initial_and_repair_calls_without_chain_mutation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    prompt = "Alpha exact specialist prompt."
    store = _Store([_agent("alpha-reviewer", prompt)], {"alpha-reviewer": prompt})
    original_chain = (
        ProviderEntry(name="codex-subscription", type="cli", transport="codex"),
        ProviderEntry(name="claude-subscription", type="cli", transport="claude"),
    )
    observed: list[tuple[tuple[str, str], ...]] = []

    def judge(task: str, _catalog: list[dict[str, Any]], **kwargs: Any) -> dict[str, Any]:
        observed.append(
            tuple((provider.name, provider.type) for provider in kwargs["config"].providers)
        )
        selected = ["alpha-reviewer"] if task.startswith("A previous evaluation") else []
        result = _judge_result(selected)
        result["provider_name"] = "zcode-recruiter"
        result["provider_attempts"] = [_attempt(name="zcode-recruiter")]
        return result

    config = AgencyConfig(
        providers=original_chain,
        inference=InferenceConfig(
            profiles={
                "zcode-recruiter": InferenceProfile(
                    name="zcode-recruiter",
                    adapter="anthropic",
                    model="GLM-5.2",
                    base_url="https://api.z.ai/api/anthropic",
                    api_key="bounded-test-key",
                )
            }
        ),
        canary=CanaryConfig(
            child_judge_provider_by_host=(("zcode", "zcode-recruiter"),),
        ),
        ollama=OllamaConfig(enabled=False),
    )
    monkeypatch.setenv("AGENCY_CANARY_MODE", "1")
    monkeypatch.setenv("AGENCY_CANARY_CHILD_JUDGE_PROVIDER", "zcode-recruiter")
    zcode_install = replace(_install(), host="zcode")
    assert store.run is not None
    store.run["host"] = "zcode"

    result = _invoke(
        monkeypatch,
        store,
        judge,
        config=config,
        host="zcode",
        install_identity=zcode_install,
        install_identity_reader=lambda _host: zcode_install,
    )

    assert result.staffed is True
    assert observed == [
        (("zcode-recruiter", "anthropic"),),
        (("zcode-recruiter", "anthropic"),),
    ]
    assert config.providers == original_chain
    assert store.decisions[-1]["decision"]["requested_provider"] == "zcode-recruiter"
    assert store.decisions[-1]["decision"]["provider"] == "zcode-recruiter"


def test_no_provider_fails_open_unstaffed_and_records_explicit_diagnostic(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    prompt = "Exact specialist prompt."
    store = _Store([_agent("alpha-reviewer", prompt)], {"alpha-reviewer": prompt})
    unavailable = {
        "selected_ids": [],
        "status": "inference_unavailable",
        "inference_mode": "unavailable",
        "error": "no inference provider is configured",
        "provider_attempts": [],
    }

    result = _invoke(monkeypatch, store, unavailable)

    assert result.staffed is False
    assert result.reason_code == "native_child_inference_unavailable"
    assert result.rewritten_task == "Review the exact authentication boundary."
    assert result.context_segment == ""
    assert result.selected_ids == ()
    assert store.prompt_reads == []
    assert result.diagnostic_decision_id == "route-1"
    failure = store.decisions[0]["decision"]
    assert failure["status"] == "inference_unavailable"
    assert failure["semantic_status"] == "inference_unavailable"
    assert failure["source"] == "native_child_inference_failure"
    assert failure["native_child_reason"] == result.reason_code
    assert failure["inference_required"] is True
    assert failure["inference_configured"] is False
    assert failure["inference_attempted"] is False
    assert store.get_native_child_staffing_decision("route-1") is None


def test_judge_cannot_mutate_the_exact_filtered_catalog_after_it_is_bound(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    prompt = "Exact specialist prompt."
    store = _Store([_agent("alpha-reviewer", prompt)], {"alpha-reviewer": prompt})

    def mutate_catalog(
        _task: str,
        candidates: list[dict[str, Any]],
        **_kwargs: Any,
    ) -> dict[str, Any]:
        candidates[0]["hash"] = _digest("mutated specialist prompt")
        return _judge_result(["alpha-reviewer"])

    monkeypatch.setattr(staffing, "query_judge", mutate_catalog)

    result = staffing.staff_native_child(
        store,
        host="claude",
        task="Review the exact authentication boundary.",
        parent_session_id="parent-session",
        parent_trace_id="parent-trace",
        launch_id="tool-use-1",
        binding_kind="launch_id",
        binding_id="tool-use-1",
        install_identity=_install(),
        install_identity_reader=lambda _host: _install(),
        config=AgencyConfig(ollama=OllamaConfig(enabled=False)),
        platform="windows",
        available_tools=(),
    )

    assert result.staffed is False
    assert result.reason_code == "native_child_routing_state_changed"
    assert store.prompt_reads == []
    assert store.decisions[0]["decision"]["status"] == "inference_invalid"


def test_roster_generation_change_after_inference_rejects_the_whole_team(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    prompt = "Exact specialist prompt."
    store = _Store([_agent("alpha-reviewer", prompt)], {"alpha-reviewer": prompt})

    def mutate_generation(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
        store.roster_generation += 1
        return _judge_result(["alpha-reviewer"])

    monkeypatch.setattr(staffing, "query_judge", mutate_generation)

    result = staffing.staff_native_child(
        store,
        host="claude",
        task="Review the exact authentication boundary.",
        parent_session_id="parent-session",
        parent_trace_id="parent-trace",
        launch_id="tool-use-1",
        binding_kind="launch_id",
        binding_id="tool-use-1",
        install_identity=_install(),
        install_identity_reader=lambda _host: _install(),
        config=AgencyConfig(ollama=OllamaConfig(enabled=False)),
        platform="windows",
        available_tools=(),
    )

    assert result.staffed is False
    assert result.reason_code == "native_child_routing_state_changed"
    assert store.prompt_reads == []
    assert all(item["decision"]["status"] != "applied" for item in store.decisions)


def test_live_disabled_config_change_after_inference_rejects_without_roster_generation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    prompt = "Exact specialist prompt."
    agent = _agent("alpha-reviewer", prompt)
    store = _Store([agent], {"alpha-reviewer": prompt})
    live_config = AgencyConfig(ollama=OllamaConfig(enabled=False))

    def capture(_store: object, config: AgencyConfig | None = None) -> RoutingSnapshot:
        effective = live_config if config is None else config
        disabled = frozenset(effective.agents.disabled)
        return RoutingSnapshot(
            config=effective,
            catalog=[] if "alpha-reviewer" in disabled else [agent],
            roster_generation=store.roster_generation,
        )

    def disable_after_inference(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
        nonlocal live_config
        live_config = replace(
            live_config,
            agents=AgentActivationConfig(disabled=("alpha-reviewer",)),
        )
        return _judge_result(["alpha-reviewer"])

    monkeypatch.setattr(staffing, "capture_routing_snapshot", capture)
    monkeypatch.setattr(staffing, "query_judge", disable_after_inference)

    result = staffing.staff_native_child(
        store,
        host="claude",
        task="Review the exact authentication boundary.",
        parent_session_id="parent-session",
        parent_trace_id="parent-trace",
        launch_id="tool-use-1",
        binding_kind="launch_id",
        binding_id="tool-use-1",
        install_identity=_install(),
        install_identity_reader=lambda _host: _install(),
        platform="windows",
        available_tools=(),
    )

    assert result.staffed is False
    assert result.reason_code == "native_child_routing_state_changed"
    assert store.prompt_reads == []
    assert all(item["decision"]["status"] != "applied" for item in store.decisions)


def test_install_identity_change_after_inference_rejects_the_whole_team(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    prompt = "Exact specialist prompt."
    store = _Store([_agent("alpha-reviewer", prompt)], {"alpha-reviewer": prompt})
    initial = _install()
    changed = replace(initial, install_id="install-2")
    identities = iter((initial, changed))

    result = _invoke(
        monkeypatch,
        store,
        _judge_result(["alpha-reviewer"]),
        install_identity=initial,
        install_identity_reader=lambda _host: next(identities),
    )

    assert result.staffed is False
    assert result.reason_code == "native_child_routing_state_changed"
    assert store.prompt_reads == []
    assert all(item["decision"]["status"] != "applied" for item in store.decisions)


def test_unverifiable_binding_kind_is_rejected_before_inference(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    prompt = "Exact specialist prompt."
    store = _Store([_agent("alpha-reviewer", prompt)], {"alpha-reviewer": prompt})

    result = _invoke(
        monkeypatch,
        store,
        _judge_result(["alpha-reviewer"]),
        binding_kind="child_session",
    )

    assert result.staffed is False
    assert result.reason_code == "native_child_request_invalid"
    assert store.prompt_reads == []
    assert store.decisions == []


@pytest.mark.parametrize(
    "selected",
    [
        ["alpha-reviewer", "alpha-reviewer"],
        ["unknown-reviewer"],
        ["alpha-reviewer", "beta-reviewer", "gamma-reviewer", "delta-reviewer"],
        "alpha-reviewer",
    ],
)
def test_invalid_duplicate_unknown_and_over_budget_inference_is_rejected_whole(
    monkeypatch: pytest.MonkeyPatch,
    selected: object,
) -> None:
    prompts = {
        slug: f"Exact {slug} prompt."
        for slug in (
            "alpha-reviewer",
            "beta-reviewer",
            "gamma-reviewer",
            "delta-reviewer",
        )
    }
    store = _Store([_agent(slug, prompt) for slug, prompt in prompts.items()], prompts)

    result = _invoke(monkeypatch, store, _judge_result(selected))

    assert result.staffed is False
    assert result.reason_code == "native_child_inference_invalid"
    assert result.context_segment == ""
    assert store.prompt_reads == []


def test_solicited_empty_selection_is_confirmed_by_one_funded_repair_call(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The judge prompt asks for zero to three specialists and tells the model to
    return an empty list when none fits, so an empty answer is a decision this
    runtime solicited. AR-255 P2 funds exactly one repair call that asks the
    judge to test that abstention against the same concrete candidate set; a
    reaffirmed empty answer is recorded under its own distinct reason so the
    next series can tell whether the repair did anything."""

    prompts = {slug: f"Exact {slug} prompt." for slug in ("alpha-reviewer", "beta-reviewer")}
    store = _Store([_agent(slug, prompt) for slug, prompt in prompts.items()], prompts)
    tasks: list[str] = []

    def judge(task: str, _candidates: list[dict[str, Any]], **_kwargs: Any) -> dict[str, Any]:
        tasks.append(task)
        return _judge_result([])

    result = _invoke(monkeypatch, store, judge)

    assert result.staffed is False
    assert result.reason_code == "native_child_abstention_confirmed"
    assert result.context_segment == ""
    assert store.prompt_reads == []
    # Exactly one funded repair: two judge calls total, never a retry loop.
    assert len(tasks) == 2
    assert tasks[0] == "Review the exact authentication boundary."
    assert tasks[1] == staffing.repair_abstention_task(tasks[0])
    # The repair tests the abstention; it never instructs a forced pick.
    assert "empty selection is the correct answer" in tasks[1]
    assert "choose" not in tasks[1].casefold()

    decision = result.routing_decision
    assert decision["status"] == "inference_abstained"
    assert decision["semantic_status"] == "inference_abstained"
    assert decision["native_child_reason"] == "native_child_abstention_confirmed"
    assert decision["inference_mode"] == "abstained"
    assert decision["inference_configured"] is True
    assert decision["inference_attempted"] is True
    assert decision["selected_ids"] == []
    # The judge answered; its confidence is the evidence that separates a
    # deliberate abstention from a provider or contract failure, which always
    # project zero.
    assert decision["confidence"] == 0.97
    assert decision["candidate_count"] == 2


def test_abstention_stands_under_legacy_reason_when_repair_cannot_run(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A repair that dies is not a confirmation. The first-pass abstention
    stands under the legacy reason, so the two outcomes stay separable."""

    prompts = {slug: f"Exact {slug} prompt." for slug in ("alpha-reviewer", "beta-reviewer")}
    store = _Store([_agent(slug, prompt) for slug, prompt in prompts.items()], prompts)
    calls: list[str] = []

    def judge(task: str, _candidates: list[dict[str, Any]], **_kwargs: Any) -> dict[str, Any]:
        calls.append(task)
        if len(calls) > 1:
            raise RuntimeError("provider offline")
        return _judge_result([])

    result = _invoke(monkeypatch, store, judge)

    assert result.staffed is False
    assert result.reason_code == "native_child_no_specialist_needed"
    assert len(calls) == 2
    decision = result.routing_decision
    assert decision["status"] == "inference_abstained"
    assert decision["native_child_reason"] == "native_child_no_specialist_needed"


def test_abstention_stands_under_legacy_reason_when_repair_answer_is_invalid(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    prompts = {slug: f"Exact {slug} prompt." for slug in ("alpha-reviewer", "beta-reviewer")}
    store = _Store([_agent(slug, prompt) for slug, prompt in prompts.items()], prompts)
    calls: list[str] = []

    def judge(task: str, _candidates: list[dict[str, Any]], **_kwargs: Any) -> dict[str, Any]:
        calls.append(task)
        if len(calls) > 1:
            return {
                "selected_ids": [],
                "status": "inference_unavailable",
                "inference_mode": "unavailable",
                "error": "configured inference providers exhausted",
                "provider_attempts": [],
            }
        return _judge_result([])

    result = _invoke(monkeypatch, store, judge)

    assert result.staffed is False
    assert result.reason_code == "native_child_no_specialist_needed"
    assert len(calls) == 2


def test_repair_selection_staffs_the_child_and_binds_the_repair_receipt(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A repair that corrects the abstention staffs the child through the same
    validation the first-pass selection would have passed, and the decision
    binds exactly the repair call's one applied provider response."""

    prompt = "Exact specialist prompt."
    store = _Store([_agent("alpha-reviewer", prompt)], {"alpha-reviewer": prompt})
    calls: list[str] = []

    def judge(task: str, _candidates: list[dict[str, Any]], **_kwargs: Any) -> dict[str, Any]:
        calls.append(task)
        if len(calls) == 1:
            return _judge_result([])
        return _judge_result(["alpha-reviewer"])

    result = _invoke(monkeypatch, store, judge)

    assert result.staffed is True
    assert result.status == "staffed"
    assert len(calls) == 2
    assert calls[1] == staffing.repair_abstention_task(calls[0])
    assert result.selected_ids == ("alpha-reviewer",)
    assert result.provider_receipt_digest == canonical_native_child_provider_receipt_digest(
        result.provider_attempts
    )
    # Exactly one applied attempt is sealed into the decision: the repair's.
    applied = [item for item in result.provider_attempts if item.get("status") == "applied"]
    assert len(applied) == 1
    [persisted] = store.decisions
    assert persisted["decision"]["selected_ids"] == ["alpha-reviewer"]
    assert persisted["decision"]["native_child_reason"] == "applied"


def test_capture_flag_records_the_redacted_child_assignment_on_a_decline(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Owner-gated instrument: with observability.capture_content on, a child
    decline writes the redacted assignment into its dedicated content lane,
    keyed to the recorded decision — and NEVER into the routing-decision
    projection, which the store strips to stay content-free. Asserting on the
    projection is exactly the mistake that shipped an inert capture once."""

    from agency_runtime.core.config import ObservabilityConfig
    from agency_runtime.core.content_redaction import redact_content

    prompts = {slug: f"Exact {slug} prompt." for slug in ("alpha-reviewer", "beta-reviewer")}
    store = _Store([_agent(slug, prompt) for slug, prompt in prompts.items()], prompts)

    result = _invoke(
        monkeypatch,
        store,
        _judge_result([]),
        config=AgencyConfig(
            ollama=OllamaConfig(enabled=False),
            observability=ObservabilityConfig(capture_content=True),
        ),
    )

    assert result.staffed is False
    assert "captured_task" not in result.routing_decision
    [captured] = store.captured_assignments
    assert captured["diagnostic_id"] == result.diagnostic_decision_id
    assert captured["captured_task"] == redact_content("Review the exact authentication boundary.")
    assert captured["task_sha256"] == result.task_sha256
    assert captured["host"] == "claude"


def test_capture_stays_absent_when_the_owner_flag_is_off(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    prompts = {slug: f"Exact {slug} prompt." for slug in ("alpha-reviewer", "beta-reviewer")}
    store = _Store([_agent(slug, prompt) for slug, prompt in prompts.items()], prompts)

    result = _invoke(monkeypatch, store, _judge_result([]))

    assert result.staffed is False
    assert "captured_task" not in result.routing_decision
    assert store.captured_assignments == []


def test_captured_assignment_survives_the_real_store_round_trip(
    tmp_path: Path,
) -> None:
    """The persistence layer itself, on a real SQLite store: the lane accepts
    a row keyed to an existing routing decision, returns it intact, and
    refuses to orphan content when the owning decision is absent."""

    store = Store(tmp_path / "agency.db")
    store.create_run(
        session_id="parent-session",
        trace_id="parent-trace",
        host="claude",
        user_message="Parent request",
    )
    task_hash = _digest("child task")
    decision_id = store.record_routing_decision(
        session_id="parent-session",
        trace_id="parent-trace",
        query_hash=task_hash,
        context_fingerprint=_digest("child context"),
        decision=staffing._routing_projection(
            result={},
            task_sha256=task_hash,
            context_fingerprint=_digest("child context"),
            selected_ids=[],
            status="inference_abstained",
            source=staffing._failure_source("inference_abstained"),
            reason_code=staffing.NATIVE_CHILD_ABSTAINED_REASON,
        ),
    )
    assert store.record_native_child_captured_assignment(
        diagnostic_id=decision_id,
        host="claude",
        parent_session_id="parent-session",
        parent_trace_id="parent-trace",
        task_sha256=task_hash,
        captured_task="Review the exact authentication boundary.",
    )
    row = store.get_native_child_captured_assignment(decision_id)
    assert row is not None
    assert row["captured_task"] == "Review the exact authentication boundary."
    assert row["task_sha256"] == task_hash
    assert row["host"] == "claude"
    # No owning decision -> no orphaned content, ever.
    assert (
        store.record_native_child_captured_assignment(
            diagnostic_id="route-nowhere",
            host="claude",
            parent_session_id="parent-session",
            parent_trace_id="parent-trace",
            task_sha256=task_hash,
            captured_task="orphan",
        )
        is False
    )
    assert store.get_native_child_captured_assignment("route-nowhere") is None


def test_repair_selection_with_invalid_receipt_leaves_the_abstention_standing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A repair selection whose receipt does not carry exactly one applied
    provider response cannot be sealed, so the abstention stands rather than
    the decision binding an unverifiable receipt."""

    prompt = "Exact specialist prompt."
    store = _Store([_agent("alpha-reviewer", prompt)], {"alpha-reviewer": prompt})
    calls: list[str] = []

    def judge(task: str, _candidates: list[dict[str, Any]], **_kwargs: Any) -> dict[str, Any]:
        calls.append(task)
        if len(calls) == 1:
            return _judge_result([])
        doubled = _judge_result(["alpha-reviewer"])
        doubled["provider_attempts"] = [_attempt(), _attempt()]
        return doubled

    result = _invoke(monkeypatch, store, judge)

    assert result.staffed is False
    assert result.reason_code == "native_child_no_specialist_needed"
    assert len(calls) == 2


def test_a_declining_judge_records_which_specialists_it_was_shown(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A count cannot answer the only question a decline raises.

    The first live child decline recorded ``candidate_count: 65`` and nothing
    else, so whether a specialist that could do the work was in front of the
    judge could only be recovered by reproducing the eligibility filter offline.
    That is the gap ``ranked_agent_ids`` closed for the parent recruiter, after
    it had already cost two days of reconstruction there.
    """

    from agency_runtime.core.store.queries import project_routing_decision

    prompts = {slug: f"Exact {slug} prompt." for slug in ("beta-reviewer", "alpha-reviewer")}
    store = _Store([_agent(slug, prompt) for slug, prompt in prompts.items()], prompts)

    decision = _invoke(monkeypatch, store, _judge_result([])).routing_decision

    # Sorted, so two runs over the same universe produce the same string, and
    # flat, so the payload cannot deepen a bounded reader past its limit.
    assert decision["offered_agent_ids"] == "alpha-reviewer~beta-reviewer"
    assert decision["offered_agent_digest"] == sha256(b"alpha-reviewer~beta-reviewer").hexdigest()
    # A solicited decline is not a failure, and an unlisted source would fall
    # through to "computed" -- reading as a deterministic decision.
    assert decision["source"] == "native_child_inference_abstained"

    projected, _work_units, source = project_routing_decision(decision)
    assert projected["offered_agent_ids"] == decision["offered_agent_ids"]
    assert projected["offered_agent_digest"] == decision["offered_agent_digest"]
    assert source == "native_child_inference_abstained"
    # Depth stays at the object itself: the string is a leaf, unlike the nested
    # list that broke the live evidence store when ranked_agent_ids shipped.
    assert isinstance(projected["offered_agent_ids"], str)


def test_a_decline_records_how_much_assignment_the_child_was_given(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Size, never content.

    `offered_agent_ids` answered "was anyone capable in front of the judge" --
    yes, and it declined anyway. What the child was *asked* is the question that
    replaced it, and the receipt is content-free by policy, so size is the
    strongest honest answer without inference or a content capture.
    """

    from agency_runtime.core.native_child_staffing import _task_shape
    from agency_runtime.core.store.queries import project_routing_decision

    prompts = {"alpha-reviewer": "Exact alpha-reviewer prompt."}
    store = _Store([_agent("alpha-reviewer", prompts["alpha-reviewer"])], prompts)

    decision = _invoke(monkeypatch, store, _judge_result([])).routing_decision
    task = "Review the exact authentication boundary."
    assert decision["task_chars"] == len(task)
    assert decision["task_lines"] == 1
    assert project_routing_decision(decision)[0]["task_chars"] == len(task)

    # A count, not a transcript: no substring of the assignment survives.
    assert _task_shape("first\nsecond\nthird") == {"task_chars": 18, "task_lines": 3}
    assert all(
        word not in json.dumps(_task_shape("SECRET child assignment"))
        for word in ("SECRET", "child", "assignment")
    )
    # Absent rather than zero when there is no assignment to describe, so a
    # missing task cannot read as an empty one.
    assert _task_shape("") == {}
    assert _task_shape(None) == {}


def test_the_offered_universe_fails_closed_rather_than_crossing_as_opaque_text() -> None:
    from agency_runtime.core.native_child_staffing import (
        MAX_RECORDED_OFFERED_AGENT_CHARS,
        _offered_projection,
    )
    from agency_runtime.core.store.queries import project_routing_decision

    def projected(value: object) -> dict[str, Any]:
        return project_routing_decision(
            {"source": "native_child_inference_abstained", "offered_agent_ids": value}
        )[0]

    assert "offered_agent_ids" not in projected("Not A Slug")
    assert "offered_agent_ids" not in projected(["alpha-reviewer"])
    assert "offered_agent_ids" not in projected("alpha-reviewer~")
    assert projected("alpha-reviewer~beta-reviewer")["offered_agent_ids"] == (
        "alpha-reviewer~beta-reviewer"
    )

    # An offered set too large to record keeps the digest, so it can never be
    # mistaken for a smaller universe than the judge actually saw.
    oversized = [f"agent-{index:04d}" for index in range(2_000)]
    projection = _offered_projection(oversized)
    assert "offered_agent_ids" not in projection
    assert (
        projection["offered_agent_digest"]
        == sha256("~".join(sorted(oversized)).encode("utf-8")).hexdigest()
    )
    assert len("~".join(sorted(oversized))) > MAX_RECORDED_OFFERED_AGENT_CHARS


def _tool_agent(slug: str, prompt: str, *, tools: tuple[str, ...]) -> dict[str, Any]:
    agent = _agent(slug, prompt)
    agent["required_tools"] = list(tools)
    return agent


def test_unsupplied_child_capability_is_proven_so_tool_cards_reach_inference(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A caller that supplies no tool set must not silently shrink the judge's
    universe. Unproven capability is not a hard eligibility ground: it removes
    every tool-declaring card before inference runs, which erases the staffing
    decision instead of enforcing it. Prove this host the way the parent adapter
    does, so the complete universe the judge is promised is the one it gets."""

    prompt = "Exact tool-reviewer prompt."
    store = _Store(
        [_tool_agent("tool-reviewer", prompt, tools=("repository-read",))],
        {
            "tool-reviewer": prompt,
        },
    )

    result = _invoke(
        monkeypatch,
        store,
        _judge_result(["tool-reviewer"]),
        available_tools=None,
        capability_status="",
    )

    assert result.staffed is True
    assert result.selected_ids == ("tool-reviewer",)


def test_explicitly_unproven_child_capability_still_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Proving capability when nothing was supplied must not weaken the fence for
    a caller that has proven the opposite. An explicit unknown status keeps every
    tool-declaring card hard-ineligible, leaving nothing for the judge to see."""

    prompt = "Exact tool-reviewer prompt."
    store = _Store(
        [_tool_agent("tool-reviewer", prompt, tools=("repository-read",))],
        {
            "tool-reviewer": prompt,
        },
    )

    result = _invoke(
        monkeypatch,
        store,
        _judge_result(["tool-reviewer"]),
        available_tools=None,
        capability_status="unknown",
    )

    assert result.staffed is False
    assert result.reason_code == "native_child_eligible_catalog_empty"


def test_compatibility_may_reject_but_never_repair_the_inference_team(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    prompts = {
        "root-reviewer": "Root exact prompt.",
        "required-reviewer": "Required exact prompt.",
    }
    store = _Store(
        [
            _agent(
                "root-reviewer",
                prompts["root-reviewer"],
                requires=("required-reviewer",),
            ),
            _agent("required-reviewer", prompts["required-reviewer"]),
        ],
        prompts,
    )

    result = _invoke(monkeypatch, store, _judge_result(["root-reviewer"]))

    assert result.staffed is False
    assert result.reason_code == "native_child_compatibility_mutated"
    assert result.selected_ids == ()
    assert store.prompt_reads == []


def test_partial_hydration_rejects_the_entire_team(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    prompts = {
        "alpha-reviewer": "Alpha exact prompt.",
        "beta-reviewer": "Beta exact prompt.",
    }
    store = _Store(
        [_agent(slug, prompt) for slug, prompt in prompts.items()],
        {"alpha-reviewer": prompts["alpha-reviewer"]},
    )

    result = _invoke(
        monkeypatch,
        store,
        _judge_result(["alpha-reviewer", "beta-reviewer"]),
    )

    assert result.staffed is False
    assert result.reason_code == "native_child_prompt_hydration_failed"
    assert store.prompt_reads == ["alpha-reviewer", "beta-reviewer"]
    assert result.context_segment == ""


def test_prompt_and_output_budgets_reject_without_truncating_a_team(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    oversized = "x" * (staffing.MAX_SPECIALIST_PROMPT_CHARS + 1)
    oversized_store = _Store(
        [_agent("alpha-reviewer", oversized)],
        {"alpha-reviewer": oversized},
    )

    prompt_result = _invoke(
        monkeypatch,
        oversized_store,
        _judge_result(["alpha-reviewer"]),
    )

    assert prompt_result.staffed is False
    assert prompt_result.reason_code == "native_child_prompt_hydration_failed"

    prompt = "Exact specialist prompt that fits its individual card ceiling."
    budget_store = _Store([_agent("alpha-reviewer", prompt)], {"alpha-reviewer": prompt})
    output_result = _invoke(
        monkeypatch,
        budget_store,
        _judge_result(["alpha-reviewer"]),
        maximum_delivery_bytes=512,
    )

    assert output_result.staffed is False
    assert output_result.reason_code == "native_child_delivery_over_budget"
    assert output_result.context_segment == ""
    assert len(budget_store.decisions) == 1
    assert budget_store.decisions[0]["decision"]["status"] == "inference_invalid"


def test_provider_receipt_must_have_exactly_one_applied_attempt(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    prompt = "Exact specialist prompt."
    store = _Store([_agent("alpha-reviewer", prompt)], {"alpha-reviewer": prompt})
    result_with_two_applied = _judge_result(["alpha-reviewer"])
    result_with_two_applied["provider_attempts"] = [_attempt(), _attempt(name="second")]

    result = _invoke(monkeypatch, store, result_with_two_applied)

    assert result.staffed is False
    assert result.reason_code == "native_child_provider_receipt_invalid"
    assert store.prompt_reads == []


def test_provider_name_uses_the_same_safe_identity_as_the_applied_receipt(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    prompt = "Exact specialist prompt."
    agent = _agent("alpha-reviewer", prompt)
    store = Store(tmp_path / "provider-identity.db")
    store.create_run(
        session_id="parent-session",
        trace_id="parent-trace",
        host="claude",
        user_message="Parent request",
    )
    monkeypatch.setattr(
        store,
        "get_routing_roster_snapshot",
        lambda **_kwargs: {
            "generation": store.get_roster_generation(),
            "catalog": [agent],
        },
    )
    monkeypatch.setattr(
        store,
        "get_versioned_specialist_prompt",
        lambda *_args, **_kwargs: {
            "slug": "alpha-reviewer",
            "version": agent["version"],
            "hash": agent["hash"],
            "prompt_body": prompt,
            "prompt_truncated": False,
        },
    )
    judge_result = _judge_result(["alpha-reviewer"])
    judge_result["provider_name"] = "valid provider name"
    judge_result["provider_attempts"] = [_attempt(name="valid provider name")]

    result = _invoke(monkeypatch, store, judge_result)

    assert result.staffed is True
    assert result.decision_id
    assert store.get_native_child_staffing_decision(result.decision_id) is not None
    conn = store._connect()
    try:
        row = conn.execute(
            "SELECT provider, decision FROM routing_decisions WHERE id = ?",
            (result.decision_id,),
        ).fetchone()
    finally:
        conn.close()
    assert row is not None
    decision = json.loads(row["decision"])
    applied_provider = decision["native_child_delivery"]["provider_attempts"][0]["provider_name"]
    assert applied_provider.startswith("sha256:")
    assert row["provider"] == decision["provider"] == applied_provider


def test_launch_child_install_time_and_nonce_bind_each_delivery_against_replay(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    prompt = "Exact specialist prompt."
    store = _Store([_agent("alpha-reviewer", prompt)], {"alpha-reviewer": prompt})
    judge_result = _judge_result(["alpha-reviewer"])
    nonces = iter(("nonce-one", "nonce-two"))
    monkeypatch.setattr(staffing, "query_judge", lambda *_args, **_kwargs: judge_result)
    monkeypatch.setattr(
        staffing,
        "_utc_now",
        lambda: datetime(2026, 8, 12, 12, 0, tzinfo=timezone.utc),
    )
    monkeypatch.setattr(staffing, "_nonce", lambda: next(nonces))
    common = {
        "store": store,
        "host": "claude",
        "task": "Review the exact authentication boundary.",
        "parent_session_id": "parent-session",
        "parent_trace_id": "parent-trace",
        "binding_kind": "child_id",
        "install_identity": _install(),
        "install_identity_reader": lambda _host: _install(),
        "config": AgencyConfig(ollama=OllamaConfig(enabled=False)),
        "platform": "windows",
        "available_tools": (),
    }

    first = staffing.staff_native_child(
        **common,
        launch_id="launch-one",
        binding_id="child-one",
    )
    second = staffing.staff_native_child(
        **common,
        launch_id="launch-two",
        binding_id="child-two",
    )

    assert first.staffed is second.staffed is True
    first_delivery = parse_inference_team_delivery(first.rewritten_task)
    second_delivery = parse_inference_team_delivery(second.rewritten_task)
    assert first_delivery is not None and second_delivery is not None
    assert first_delivery.launch_id == "launch-one"
    assert second_delivery.launch_id == "launch-two"
    assert first_delivery.binding_id == "child-one"
    assert second_delivery.binding_id == "child-two"
    assert first_delivery.nonce == "nonce-one"
    assert second_delivery.nonce == "nonce-two"
    assert first_delivery.install_id == second_delivery.install_id == "install-1"
    assert first_delivery.runtime_digest == second_delivery.runtime_digest == _digest("runtime")
    assert first.rewritten_task != second.rewritten_task
    assert first.team_digest == second.team_digest


def test_install_identity_drift_fails_before_inference(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    prompt = "Exact specialist prompt."
    store = _Store([_agent("alpha-reviewer", prompt)], {"alpha-reviewer": prompt})
    called = False

    def judge(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
        nonlocal called
        called = True
        return _judge_result(["alpha-reviewer"])

    monkeypatch.setattr(staffing, "query_judge", judge)
    drifted = replace(_install(), candidate_digest=_digest("different-runtime"))

    result = staffing.staff_native_child(
        store,
        host="claude",
        task="Review the exact authentication boundary.",
        parent_session_id="parent-session",
        parent_trace_id="parent-trace",
        launch_id="tool-use-1",
        binding_kind="launch_id",
        binding_id="tool-use-1",
        install_identity=drifted,
        install_identity_reader=lambda _host: _install(),
    )

    assert result.staffed is False
    assert result.reason_code == "native_child_install_identity_invalid"
    assert called is False
    assert len(store.decisions) == 1
    failure = store.decisions[0]["decision"]
    assert failure["status"] == "inference_invalid"
    assert failure["native_child_reason"] == "native_child_install_identity_invalid"
    assert failure["inference_configured"] is False
    assert failure["inference_attempted"] is False


@pytest.mark.parametrize(
    "run",
    [
        None,
        {
            "trace_id": "parent-trace",
            "session_id": "different-session",
            "host": "claude",
            "status": "active",
        },
        {
            "trace_id": "parent-trace",
            "session_id": "parent-session",
            "host": "codex",
            "status": "active",
        },
        {
            "trace_id": "parent-trace",
            "session_id": "parent-session",
            "host": "claude",
            "status": "completed",
        },
    ],
)
def test_missing_mismatched_or_terminal_parent_cannot_staff_or_fabricate_a_run(
    monkeypatch: pytest.MonkeyPatch,
    run: dict[str, Any] | None,
) -> None:
    prompt = "Exact specialist prompt."
    store = _Store([_agent("alpha-reviewer", prompt)], {"alpha-reviewer": prompt})
    store.run = run
    called = False

    def judge(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
        nonlocal called
        called = True
        return _judge_result(["alpha-reviewer"])

    monkeypatch.setattr(staffing, "query_judge", judge)

    result = staffing.staff_native_child(
        store,
        host="claude",
        task="Review the exact authentication boundary.",
        parent_session_id="parent-session",
        parent_trace_id="parent-trace",
        launch_id="tool-use-1",
        binding_kind="launch_id",
        binding_id="tool-use-1",
        install_identity=_install(),
        install_identity_reader=lambda _host: _install(),
    )

    assert result.staffed is False
    assert result.reason_code == "native_child_parent_scope_invalid"
    assert result.context_segment == ""
    assert called is False
    assert store.decisions == []


def test_public_failure_recorder_binds_launch_without_storing_task_content() -> None:
    prompt = "Exact specialist prompt."
    store = _Store([_agent("alpha-reviewer", prompt)], {"alpha-reviewer": prompt})
    task = "Confidential opaque child assignment."

    unavailable_id = staffing.record_native_child_staffing_failure(
        store,
        host="claude",
        task=task,
        parent_session_id="parent-session",
        parent_trace_id="parent-trace",
        launch_id="opaque-launch-1",
        reason_code="unsupported_opaque_interagent_channel",
    )
    invalid_id = staffing.record_native_child_staffing_failure(
        store,
        host="claude",
        task=task,
        parent_session_id="parent-session",
        parent_trace_id="parent-trace",
        launch_id="overflow-launch-2",
        reason_code="native_child_delivery_over_budget",
        inference_configured=True,
        inference_attempted=True,
    )

    assert unavailable_id == "route-1"
    assert invalid_id == "route-2"
    unavailable = store.decisions[0]["decision"]
    invalid = store.decisions[1]["decision"]
    assert unavailable["status"] == unavailable["semantic_status"] == "inference_unavailable"
    assert unavailable["native_child_reason"] == "unsupported_opaque_interagent_channel"
    assert unavailable["inference_configured"] is False
    assert unavailable["inference_attempted"] is False
    assert invalid["status"] == invalid["semantic_status"] == "inference_invalid"
    assert invalid["native_child_reason"] == "native_child_delivery_over_budget"
    assert invalid["inference_configured"] is True
    assert invalid["inference_attempted"] is True
    assert store.decisions[0]["context_fingerprint"] != store.decisions[1]["context_fingerprint"]
    assert task not in repr(store.decisions)


def test_public_failure_recorder_rejects_bad_correlation_parent_and_reason() -> None:
    prompt = "Exact specialist prompt."
    store = _Store([_agent("alpha-reviewer", prompt)], {"alpha-reviewer": prompt})
    common = {
        "store": store,
        "host": "claude",
        "task": "Review the exact authentication boundary.",
        "parent_session_id": "parent-session",
        "parent_trace_id": "parent-trace",
        "launch_id": "launch-1",
        "reason_code": "native_child_delivery_over_budget",
    }

    assert (
        staffing.record_native_child_staffing_failure(
            **{**common, "launch_id": "contains\ncontrol"}
        )
        == ""
    )
    assert (
        staffing.record_native_child_staffing_failure(**{**common, "reason_code": "x" * 65}) == ""
    )
    store.run = {**store.run, "session_id": "different-session"}  # type: ignore[arg-type]
    assert staffing.record_native_child_staffing_failure(**common) == ""
    assert store.decisions == []


def test_public_failure_projection_round_trips_through_real_store(tmp_path: Path) -> None:
    store = Store(tmp_path / "agency.db")
    store.create_run(
        session_id="parent-session",
        trace_id="parent-trace",
        host="claude",
        user_message="Parent request",
    )

    decision_id = staffing.record_native_child_staffing_failure(
        store,
        host="claude",
        task="Confidential opaque child assignment.",
        parent_session_id="parent-session",
        parent_trace_id="parent-trace",
        launch_id="opaque-launch-1",
        reason_code="unsupported_opaque_interagent_channel",
    )

    conn = store._connect()
    try:
        row = conn.execute(
            "SELECT status, source, decision FROM routing_decisions WHERE id = ?",
            (decision_id,),
        ).fetchone()
    finally:
        conn.close()
    assert row is not None
    projection = json.loads(row["decision"])
    assert row["status"] == projection["status"] == "inference_unavailable"
    assert row["source"] == projection["source"] == "native_child_inference_failure"
    assert projection["native_child_reason"] == "unsupported_opaque_interagent_channel"
    assert projection["inference_required"] is True
    assert store.get_native_child_staffing_decision(decision_id) is None


def test_the_offered_universe_survives_a_real_store_write_and_read(tmp_path: Path) -> None:
    """The projection accepting a field is not evidence the reader returns it.

    ``ranked_agent_ids`` passed its own projection and still bricked the live
    evidence store, because the reader applied a bound the writer never saw. A
    decline is only diagnosable if the offered set survives the whole path.
    """

    store = Store(tmp_path / "agency.db")
    store.create_run(
        session_id="parent-session",
        trace_id="parent-trace",
        host="claude",
        user_message="Parent request",
    )
    offered = sorted(f"agent-{index:03d}" for index in range(64))
    decision_id = store.record_routing_decision(
        session_id="parent-session",
        trace_id="parent-trace",
        query_hash=_digest("child task"),
        context_fingerprint=_digest("child context"),
        decision=staffing._routing_projection(
            result={"candidate_count": len(offered)},
            task_sha256=_digest("child task"),
            context_fingerprint=_digest("child context"),
            selected_ids=[],
            status="inference_abstained",
            source=staffing._failure_source("inference_abstained"),
            reason_code=staffing.NATIVE_CHILD_ABSTAINED_REASON,
            offered_ids=offered,
        ),
    )

    conn = store._connect()
    try:
        row = conn.execute(
            "SELECT source, decision FROM routing_decisions WHERE id = ?",
            (decision_id,),
        ).fetchone()
    finally:
        conn.close()
    assert row is not None
    projection = json.loads(row["decision"])
    assert row["source"] == "native_child_inference_abstained"
    assert projection["offered_agent_ids"] == "~".join(offered)
    assert projection["offered_agent_digest"] == _digest("~".join(offered))
    assert projection["candidate_count"] == 64
    # Every recent-activity reader decodes the same row; a payload that only the
    # writer accepts is how the store was bricked before.
    assert any(item.get("id") == decision_id for item in store.recent_runtime_activity()["routing"])


def test_route_persistence_failure_returns_original_task_without_delivery(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    prompt = "Exact specialist prompt."
    store = _Store([_agent("alpha-reviewer", prompt)], {"alpha-reviewer": prompt})
    monkeypatch.setattr(store, "record_routing_decision", lambda **_kwargs: "")

    result = _invoke(monkeypatch, store, _judge_result(["alpha-reviewer"]))

    assert result.staffed is False
    assert result.reason_code == "native_child_routing_decision_unavailable"
    assert result.rewritten_task == "Review the exact authentication boundary."
    assert result.context_segment == ""
    assert result.decision_id == ""


def test_final_delivery_validation_failure_returns_no_applied_delivery(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    prompt = "Exact specialist prompt."
    store = _Store([_agent("alpha-reviewer", prompt)], {"alpha-reviewer": prompt})

    result = _invoke(
        monkeypatch,
        store,
        _judge_result(["alpha-reviewer"]),
        final_delivery_validator=lambda: False,
    )

    assert result.staffed is False
    assert result.reason_code == "native_child_routing_decision_unavailable"
    assert result.context_segment == ""
    assert [item["decision"]["status"] for item in store.decisions] == ["inference_invalid"]


def test_real_store_final_validation_rejection_leaves_no_applied_route_and_retries(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    prompt = "Exact specialist prompt."
    agent = _agent("alpha-reviewer", prompt)
    store = Store(tmp_path / "final-validation.db")
    store.create_run(
        session_id="parent-session",
        trace_id="parent-trace",
        host="claude",
        user_message="Parent request",
    )
    monkeypatch.setattr(
        store,
        "get_routing_roster_snapshot",
        lambda **_kwargs: {
            "generation": store.get_roster_generation(),
            "catalog": [agent],
        },
    )
    monkeypatch.setattr(
        store,
        "get_versioned_specialist_prompt",
        lambda *_args, **_kwargs: {
            "slug": "alpha-reviewer",
            "version": agent["version"],
            "hash": agent["hash"],
            "prompt_body": prompt,
            "prompt_truncated": False,
        },
    )
    freshness = iter([False, True])

    rejected = _invoke(
        monkeypatch,
        store,  # type: ignore[arg-type]
        _judge_result(["alpha-reviewer"]),
        final_delivery_validator=lambda: next(freshness),
    )

    assert rejected.staffed is False
    assert rejected.reason_code == "native_child_routing_decision_unavailable"
    conn = store._connect()
    try:
        assert (
            conn.execute(
                "SELECT COUNT(*) FROM routing_decisions "
                "WHERE source = 'native_child_inference' AND status = 'applied'"
            ).fetchone()[0]
            == 0
        )
    finally:
        conn.close()

    retried = _invoke(
        monkeypatch,
        store,  # type: ignore[arg-type]
        _judge_result(["alpha-reviewer"]),
        final_delivery_validator=lambda: next(freshness),
    )

    assert retried.staffed is True
    assert retried.decision_id
    assert store.get_native_child_staffing_decision(retried.decision_id) is not None


def test_config_lock_exit_failure_preserves_committed_staffed_delivery(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    prompt = "Exact specialist prompt."
    store = _Store([_agent("alpha-reviewer", prompt)], {"alpha-reviewer": prompt})

    @contextmanager
    def fail_after_commit() -> Iterator[None]:
        yield
        raise RuntimeError("lock release failed after commit")

    monkeypatch.setattr(
        staffing,
        "_native_child_config_read_lock",
        lambda _store: fail_after_commit(),
    )

    result = _invoke(monkeypatch, store, _judge_result(["alpha-reviewer"]))

    assert result.staffed is True
    assert result.decision_id
    assert [item["decision"]["status"] for item in store.decisions] == ["applied"]


@pytest.mark.parametrize("warning_fails", [False, True])
def test_postcommit_connection_close_failure_preserves_exact_staffed_output(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    warning_fails: bool,
) -> None:
    prompt = "Exact specialist prompt."
    agent = _agent("alpha-reviewer", prompt)
    store = Store(tmp_path / "postcommit-close.db")
    store.create_run(
        session_id="parent-session",
        trace_id="parent-trace",
        host="claude",
        user_message="Parent request",
    )
    monkeypatch.setattr(
        store,
        "get_routing_roster_snapshot",
        lambda **_kwargs: {
            "generation": store.get_roster_generation(),
            "catalog": [agent],
        },
    )
    monkeypatch.setattr(
        store,
        "get_versioned_specialist_prompt",
        lambda *_args, **_kwargs: {
            "slug": "alpha-reviewer",
            "version": agent["version"],
            "hash": agent["hash"],
            "prompt_body": prompt,
            "prompt_truncated": False,
        },
    )
    real_connect = store._connect

    class _PostcommitCloseFailure:
        def __init__(self) -> None:
            self._connection = real_connect()
            self._committed = False

        def __getattr__(self, name: str) -> Any:
            return getattr(self._connection, name)

        def commit(self) -> None:
            self._connection.commit()
            self._committed = True

        def close(self) -> None:
            self._connection.close()
            if self._committed:
                raise RuntimeError("postcommit close failed")

    monkeypatch.setattr(store, "_connect", _PostcommitCloseFailure)
    if warning_fails:
        monkeypatch.setattr(
            maintenance.logger,
            "warning",
            lambda *_args, **_kwargs: (_ for _ in ()).throw(
                RuntimeError("postcommit warning failed")
            ),
        )

    result = _invoke(monkeypatch, store, _judge_result(["alpha-reviewer"]))

    assert result.staffed is True
    assert result.decision_id
    resolved = store.get_native_child_staffing_decision(result.decision_id)
    assert resolved is not None
    assert resolved["decision_id"] == result.decision_id


def test_exact_render_failure_happens_before_any_applied_route(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    prompt = "Exact specialist prompt."
    store = _Store([_agent("alpha-reviewer", prompt)], {"alpha-reviewer": prompt})
    monkeypatch.setattr(
        staffing,
        "render_inference_team_delivery",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(ValueError("render failed")),
    )

    result = _invoke(monkeypatch, store, _judge_result(["alpha-reviewer"]))

    assert result.staffed is False
    assert result.reason_code == "native_child_delivery_render_failed"
    assert all(item["decision"]["status"] != "applied" for item in store.decisions)


def test_pure_delivery_validator_rejects_before_any_applied_route(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    prompt = "Exact specialist prompt."
    store = _Store([_agent("alpha-reviewer", prompt)], {"alpha-reviewer": prompt})
    observed: list[str] = []

    result = _invoke(
        monkeypatch,
        store,
        _judge_result(["alpha-reviewer"]),
        delivery_validator=lambda rewritten: observed.append(rewritten) is None and False,
    )

    assert result.staffed is False
    assert result.reason_code == "native_child_delivery_validation_failed"
    assert len(observed) == 1
    assert parse_inference_team_delivery(observed[0]) is not None
    assert all(item["decision"]["status"] != "applied" for item in store.decisions)


def test_store_proposed_decision_id_collision_rolls_back_atomically(tmp_path: Path) -> None:
    store = Store(tmp_path / "collision.db")
    store.create_run(
        session_id="parent-session",
        trace_id="parent-trace",
        host="claude",
        user_message="Parent request",
    )
    first_id = store.record_routing_decision(
        trace_id="parent-trace",
        session_id="parent-session",
        query_hash=_digest("first"),
        context_fingerprint=_digest("first-context"),
        decision={"status": "inference_invalid"},
        decision_id="collision-route",
    )

    with pytest.raises(sqlite3.IntegrityError):
        store.record_routing_decision(
            trace_id="parent-trace",
            session_id="parent-session",
            query_hash=_digest("second"),
            context_fingerprint=_digest("second-context"),
            decision={"status": "applied"},
            decision_id="collision-route",
        )

    assert first_id == "collision-route"
    conn = store._connect()
    try:
        rows = conn.execute(
            "SELECT id, status FROM routing_decisions WHERE id = ?",
            ("collision-route",),
        ).fetchall()
    finally:
        conn.close()
    assert [(row["id"], row["status"]) for row in rows] == [
        ("collision-route", "inference_invalid")
    ]


def test_staffing_proposed_id_collision_never_creates_a_second_applied_route(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    prompt = "Exact specialist prompt."
    store = _Store([_agent("alpha-reviewer", prompt)], {"alpha-reviewer": prompt})
    store.decision_ids.add("collision-route")
    monkeypatch.setattr(staffing, "_decision_id", lambda: "collision-route")

    result = _invoke(monkeypatch, store, _judge_result(["alpha-reviewer"]))

    assert result.staffed is False
    assert result.reason_code == "native_child_routing_decision_unavailable"
    assert all(item["decision"]["status"] != "applied" for item in store.decisions)


def test_parent_closing_after_precheck_cannot_receive_an_applied_route(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    prompt = "Exact specialist prompt."
    store = _Store([_agent("alpha-reviewer", prompt)], {"alpha-reviewer": prompt})
    store.close_before_record = True

    result = _invoke(monkeypatch, store, _judge_result(["alpha-reviewer"]))

    assert result.staffed is False
    assert result.reason_code == "native_child_routing_decision_unavailable"
    assert store.decisions == []


def test_disabling_selected_agent_inside_route_recorder_cannot_commit_applied_route(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    prompt = "Exact specialist prompt."
    store = _Store([_agent("alpha-reviewer", prompt)], {"alpha-reviewer": prompt})
    store.disable_before_record = True

    result = _invoke(monkeypatch, store, _judge_result(["alpha-reviewer"]))

    assert result.staffed is False
    assert result.reason_code == "native_child_routing_decision_unavailable"
    assert all(item["decision"]["status"] != "applied" for item in store.decisions)


def test_final_live_reload_and_route_insert_share_the_config_read_lock(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    prompt = "Exact specialist prompt."
    store = _Store([_agent("alpha-reviewer", prompt)], {"alpha-reviewer": prompt})
    lock_held = False
    snapshot_lock_states: list[bool] = []
    original_snapshot = staffing.capture_routing_snapshot
    original_record = store.record_routing_decision

    @contextmanager
    def guarded_slice() -> Any:
        nonlocal lock_held
        assert lock_held is False
        lock_held = True
        try:
            yield
        finally:
            lock_held = False

    def capture(*args: Any, **kwargs: Any) -> RoutingSnapshot:
        snapshot_lock_states.append(lock_held)
        return original_snapshot(*args, **kwargs)

    def record(**values: Any) -> str:
        if values["decision"]["status"] == "applied":
            assert lock_held is True
        return original_record(**values)

    monkeypatch.setattr(staffing, "_native_child_config_read_lock", lambda _store: guarded_slice())
    monkeypatch.setattr(staffing, "capture_routing_snapshot", capture)
    monkeypatch.setattr(store, "record_routing_decision", record)

    result = _invoke(monkeypatch, store, _judge_result(["alpha-reviewer"]))

    assert result.staffed is True
    assert snapshot_lock_states == [False, False, True]
    assert lock_held is False


def test_store_open_run_and_roster_guards_are_atomic_with_route_insert(tmp_path: Path) -> None:
    store = Store(tmp_path / "route-guard.db")
    store.create_run(
        session_id="parent-session",
        trace_id="parent-trace",
        host="claude",
        user_message="Parent request",
    )
    generation = store.get_roster_generation()
    assert (
        store.close_turn_evidence(
            "parent-session",
            "parent-trace",
            status="preflight_failed",
        )
        == 1
    )

    with pytest.raises(ValueError, match="terminal turn"):
        store.record_routing_decision(
            trace_id="parent-trace",
            session_id="parent-session",
            query_hash=_digest("guarded"),
            context_fingerprint=_digest("guarded-context"),
            decision={"status": "applied"},
            decision_id="guarded-route",
            require_open_run=True,
            expected_roster_generation=generation,
        )

    conn = store._connect()
    try:
        assert (
            conn.execute(
                "SELECT 1 FROM routing_decisions WHERE id = ?",
                ("guarded-route",),
            ).fetchone()
            is None
        )
    finally:
        conn.close()


def test_store_activation_policy_guard_rolls_back_change_after_route_insert(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = Store(tmp_path / "activation-policy-guard.db")
    store.create_run(
        session_id="parent-session",
        trace_id="parent-trace",
        host="claude",
        user_message="Parent request",
    )
    expected = tuple(sorted(store.get_disabled_agent_slugs()))
    changed = set(expected)
    race_slug = "atomic-policy-race"
    if race_slug in changed:
        changed.remove(race_slug)
    else:
        changed.add(race_slug)
    reads = 0

    def changing_policy() -> frozenset[str]:
        nonlocal reads
        reads += 1
        return frozenset(expected if reads == 1 else changed)

    monkeypatch.setattr(store, "get_disabled_agent_slugs", changing_policy)

    with pytest.raises(ValueError, match="activation policy changed"):
        store.record_routing_decision(
            trace_id="parent-trace",
            session_id="parent-session",
            query_hash=_digest("policy-guarded"),
            context_fingerprint=_digest("policy-guarded-context"),
            decision={"status": "applied"},
            decision_id="policy-guarded-route",
            require_open_run=True,
            expected_roster_generation=store.get_roster_generation(),
            expected_disabled_agents=expected,
        )

    assert reads == 2
    conn = store._connect()
    try:
        assert (
            conn.execute(
                "SELECT 1 FROM routing_decisions WHERE id = ?",
                ("policy-guarded-route",),
            ).fetchone()
            is None
        )
    finally:
        conn.close()


def test_team_scope_narrows_judge_candidates_and_still_commits(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # ADR-0194 regression: the 2026-08-30 live canary failed every guarded
    # commit with native_child_routing_state_changed because the decision
    # fingerprint hashed the scoped catalog while the commit re-check hashed
    # the unscoped one. The fingerprint is a routing-authority digest; the
    # scope only narrows what the judge may select.
    prompts = {
        "alpha-reviewer": "Alpha exact specialist prompt.",
        "beta-reviewer": "Beta exact specialist prompt.",
    }
    catalog = [
        _agent("alpha-reviewer", prompts["alpha-reviewer"]),
        _agent("beta-reviewer", prompts["beta-reviewer"]),
    ]
    store = _Store(catalog, prompts)
    observed: list[list[str]] = []

    def judge(_task: str, candidates: list[dict[str, Any]], **_kwargs: Any) -> dict[str, Any]:
        observed.append([str(item["slug"]) for item in candidates])
        return _judge_result(["alpha-reviewer"])

    result = _invoke(monkeypatch, store, judge, team_scope=("alpha-reviewer",))

    assert observed == [["alpha-reviewer"]]
    assert result.staffed is True
    assert result.selected_ids == ("alpha-reviewer",)


def test_empty_team_scope_fails_closed_before_the_judge(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    prompts = {"alpha-reviewer": "Alpha exact specialist prompt."}
    store = _Store([_agent("alpha-reviewer", prompts["alpha-reviewer"])], prompts)

    def forbidden_judge(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
        raise AssertionError("the judge must not run over an empty scoped pool")

    result = _invoke(monkeypatch, store, forbidden_judge, team_scope=("absent-slug",))

    assert result.staffed is False
    assert result.reason_code == "native_child_eligible_catalog_empty"
