"""Inference-owned, authority-bounded Codex activation-canary routing."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from agency_runtime.core import canary
from agency_runtime.core.activation_canary_contract import (
    CODEX_ACTIVATION_CANARY_PROMPT,
    CODEX_ACTIVATION_CANARY_ROUTE_SOURCE,
    CODEX_ACTIVATION_CANARY_WORK_UNIT,
    is_exact_codex_activation_canary_task,
)
from agency_runtime.core.config import AgencyConfig
from agency_runtime.core.workforce.inference import _explicit_indivisible_unit_request
from agency_runtime.core.host_capabilities import native_adapter_capability_receipt
from agency_runtime.core.selector import pipeline
from agency_runtime.core.selector.cache import clear_cache
from agency_runtime.core.selector.stickiness import clear_session_routing
from agency_runtime.core.unit_assignment import (
    MAX_WORK_UNIT_CHARS,
)

_CANARY_ENV = {
    "AGENCY_CANARY_MODE": "1",
    "AGENCY_CANARY_REQUIRE_EXISTING_STORE": "1",
}


def _task(nonce: str = "a" * 32) -> str:
    return f"{CODEX_ACTIVATION_CANARY_PROMPT}\n\nCanary nonce: {nonce}"


def _catalog(*, required_tools: list[str] | None = None) -> list[dict[str, Any]]:
    return [
        {
            "slug": "code-reviewer",
            "name": "Code Reviewer",
            "description": "Reviews code for behavioral regressions and test gaps.",
            "categories": ["code", "review", "quality"],
            "capabilities": ["code review", "bug finding", "test assessment"],
            "supported_hosts": ["codex"],
            "supported_platforms": ["windows"],
            "authority": "review",
            "task_types": ["analysis", "review"],
            "context_mode": "direct_safe",
            "required_tools": required_tools or [],
            "evidence_requirements": [],
        }
    ]


def _route(
    monkeypatch: pytest.MonkeyPatch,
    *,
    catalog: list[dict[str, Any]] | None = None,
    set_canary_env: bool = True,
) -> dict[str, Any]:
    session_id = "activation-canary-contract"
    trace_id = "activation-canary-contract-trace"
    if set_canary_env:
        for name, value in _CANARY_ENV.items():
            monkeypatch.setenv(name, value)
    capability = native_adapter_capability_receipt(
        "codex",
        platform="windows",
        session_id=session_id,
        trace_id=trace_id,
        available_tools=("repository-read", "native-delegation"),
    )
    snapshot = SimpleNamespace(
        generation=7,
        worker_count=1,
        contract_fingerprint="sha256:" + "a" * 64,
    )
    return pipeline.route(
        session_id,
        _task(),
        _catalog() if catalog is None else catalog,
        config=AgencyConfig(),
        trace_id=trace_id,
        host="codex",
        platform="windows",
        capability_receipt=capability,
        workforce_snapshot=snapshot,
    )


@pytest.mark.parametrize(
    ("task", "host", "status", "environ"),
    [
        (_task(), "claude", "native-contract-verified", _CANARY_ENV),
        (_task(), "codex", "explicit", _CANARY_ENV),
        (_task(), "codex", "native-contract-verified", {"AGENCY_CANARY_MODE": "1"}),
        (
            _task(),
            "codex",
            "native-contract-verified",
            {"AGENCY_CANARY_REQUIRE_EXISTING_STORE": "1"},
        ),
        (_task("A" * 32), "codex", "native-contract-verified", _CANARY_ENV),
        (_task("a" * 31), "codex", "native-contract-verified", _CANARY_ENV),
        (_task("a" * 33), "codex", "native-contract-verified", _CANARY_ENV),
        (
            _task().replace("\n\n", "\r\n\r\n"),
            "codex",
            "native-contract-verified",
            _CANARY_ENV,
        ),
        (_task() + " ", "codex", "native-contract-verified", _CANARY_ENV),
        ("Canary nonce: " + "a" * 32, "codex", "native-contract-verified", _CANARY_ENV),
    ],
)
def test_activation_canary_task_recognition_is_closed_world(
    task: str,
    host: str,
    status: str,
    environ: dict[str, str],
) -> None:
    assert not is_exact_codex_activation_canary_task(
        task,
        host=host,
        capability_status=status,
        environ=environ,
    )


def test_activation_canary_task_recognizes_only_exact_native_probe() -> None:
    assert is_exact_codex_activation_canary_task(
        _task(),
        host="codex",
        capability_status="native-contract-verified",
        environ=_CANARY_ENV,
    )


def test_activation_canary_prompt_and_unit_fit_every_transport_bound() -> None:
    task = _task()
    assert len(task) <= pipeline.MAX_ROUTING_SIGNAL_CHARS
    assert len(CODEX_ACTIVATION_CANARY_WORK_UNIT) <= MAX_WORK_UNIT_CHARS
    assert CODEX_ACTIVATION_CANARY_WORK_UNIT != CODEX_ACTIVATION_CANARY_PROMPT
    assert " ".join(task.split()) != CODEX_ACTIVATION_CANARY_WORK_UNIT
    assert "Canary nonce:" not in CODEX_ACTIVATION_CANARY_WORK_UNIT
    assert canary.CANARY_PROMPT == CODEX_ACTIVATION_CANARY_PROMPT


def test_activation_canary_prompt_is_pinned_verbatim() -> None:
    # Golden pin (AR-255 instrument fix): the prompt is a wire format. The
    # codex recognizer fullmatches its exact text and the captured-assignment
    # acceptance compares the child's assignment to the work unit for exact
    # equality, so every wording change must be deliberate and must arrive
    # here in the same commit; an insertion mid-prompt must not pass.
    assert CODEX_ACTIVATION_CANARY_PROMPT == (
        "Treat this as exactly one indivisible code-review work unit. Delegate "
        "that complete work unit to exactly one sub-agent, spawn no other "
        "sub-agents this turn, and do not inspect the environment before or "
        "after delegating. The sub-agent's complete assignment must be exactly "
        "the work unit text below, nothing before it and nothing after it: no "
        'role, no persona, no "you are acting as..." preamble, no review '
        "instructions of your own, and no canary framing; your runtime staffs "
        'sub-agents with any expertise they need. A trailing "Canary nonce" '
        "line is not part of the work unit; never pass it to the sub-agent.\n"
        "Work unit:\n"
        "Identify the primary behavioral regression risk of replacing return "
        "value with return value.strip() in a Python text-normalization helper."
    )


def test_activation_canary_prompt_declares_one_indivisible_unit() -> None:
    # The one-unit routing constraint must keep firing on the exact prompt, or
    # the planner regains license to decompose the canary turn into errands.
    assert _explicit_indivisible_unit_request(CODEX_ACTIVATION_CANARY_PROMPT) is True


def _inferred_projection(*, selected: str = "code-reviewer") -> dict[str, Any]:
    work_unit_id = "unit-1111111111"
    return {
        "selected_ids": [selected],
        "semantic_ids": [selected],
        "confidence": 0.99,
        "margin": 0.5,
        "status": "accepted",
        "source": "workforce_inference",
        "inference_required": True,
        "inference_attempted": True,
        "inference_mode": "inferred",
        "provider_attempts": [{"stage": "planner", "status": "applied"}],
        "work_units": {
            "count": 1,
            "confidence": "high",
            "source": "verified-workforce-plan",
            "units": ["provider-derived diagnostic unit"],
            "delegate": True,
        },
        "workforce_unit_descriptors": [
            {
                "ordinal": 1,
                "artifact_kind": "review-report",
                "lifecycle_phase": "review",
                "authority": "review",
            }
        ],
        "workforce_unit_bindings": [
            {
                "source_unit_id": "unit-work",
                "work_unit_id": work_unit_id,
                "selected": [selected],
                "delivery": "delegate",
                "timing": "immediate",
                "depends_on": [],
                "parallelization": "sequential",
                "mutation_scope": "read_only",
                "artifact_kind": "review-report",
                "required_tools": [],
                "required_evidence": ["review-report"],
                "confidence": 0.99,
            }
        ],
        "unit_assignment_agents": [
            {
                "slug": selected,
                "name": "Inference-selected reviewer",
                "description": "Reviews the bounded diagnostic.",
                "capabilities": ["code review"],
                "tags": ["review"],
                "required_tools": [],
                "evidence_requirements": ["review-report"],
                "matched_work_unit_ids": [work_unit_id],
                "primary_work_unit_ids": [work_unit_id],
            }
        ],
    }


def test_activation_canary_uses_inference_owned_selection(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from agency_runtime.core.workforce import inference, routing_projection

    clear_cache()
    clear_session_routing()
    calls: list[str] = []
    planner_options: list[dict[str, Any]] = []
    outcome = SimpleNamespace(attempts=())

    def planner(message: str, *_args: Any, **_kwargs: Any) -> Any:
        calls.append(message)
        planner_options.append(_kwargs)
        return outcome

    monkeypatch.setattr(inference, "plan_and_staff_workforce", planner)
    monkeypatch.setattr(
        pipeline,
        "_run_gap_hiring",
        lambda *_args, **_kwargs: pytest.fail(
            "the read-only activation canary must not enter gap hiring"
        ),
    )
    monkeypatch.setattr(
        routing_projection,
        "project_workforce_routing",
        lambda *_args, **_kwargs: _inferred_projection(),
    )

    result = _route(monkeypatch)

    assert calls == [_task()]
    assert planner_options[0]["max_planned_units"] == 1
    assert planner_options[0]["required_planned_artifact_kind"] == "review-report"
    assert result["source"] == CODEX_ACTIVATION_CANARY_ROUTE_SOURCE
    assert result["selected_ids"] == ["code-reviewer"]
    assert result["inference_required"] is True
    assert result["inference_attempted"] is True
    assert result["provider_attempts"]
    assert result["work_units"] == {
        "count": 1,
        "confidence": "high",
        "source": "activation-canary-contract",
        "units": [CODEX_ACTIVATION_CANARY_WORK_UNIT],
        "delegate": True,
    }
    assert "workforce_unit_descriptors" not in result

    # What the canary proves stops here: inference picked the specialist. It
    # used to go on to build and hydrate a unit-agent plan, but planning work
    # units is Job B and the card goes to whoever the harness already spawned.
    assert result["work_units"]["units"] == [CODEX_ACTIVATION_CANARY_WORK_UNIT]


def test_existing_store_product_canary_can_hire_an_inference_declared_gap(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from agency_runtime.core.workforce import hiring as hiring_module

    for name, value in _CANARY_ENV.items():
        monkeypatch.setenv(name, value)
    unit_id = "unit-05-documentation"
    unit = SimpleNamespace(unit_id=unit_id)
    outcome = SimpleNamespace(
        inference_mode="inferred",
        attempts=(SimpleNamespace(status="applied"),),
        plan=SimpleNamespace(units=(unit,)),
        proposal=SimpleNamespace(
            units=(
                SimpleNamespace(
                    unit_id=unit_id,
                    abstention_reasons=("inference-declared-gap",),
                ),
            )
        ),
        staffing=SimpleNamespace(
            abstention_reasons=(
                SimpleNamespace(
                    unit_id=unit_id,
                    code="required_agents_missing",
                ),
                SimpleNamespace(
                    unit_id=unit_id,
                    code="no_safe_sufficient_team",
                ),
                SimpleNamespace(
                    unit_id=unit_id,
                    code="recruiter_abstained",
                ),
            )
        ),
    )
    request = SimpleNamespace(
        user_message="Build the complete application in this workspace.",
        host="codex",
        platform="windows",
        available_tools=("repository-write", "test-execution"),
        session_id="product-canary-session",
        trace_id="product-canary-trace",
    )
    snapshot = SimpleNamespace(generation=7, contracts=())
    calls: list[str] = []

    def hire(*_args: Any, **_kwargs: Any) -> SimpleNamespace:
        calls.append(unit_id)
        return SimpleNamespace(
            status="declined",
            reason_codes=("hiring_response_invalid",),
            hiring_case=None,
            worker=None,
            notification="",
            attempts=(),
            workforce_changed=False,
            pending_commit=None,
        )

    monkeypatch.setattr(hiring_module, "hire_contractor_for_gap", hire)

    routed, routed_snapshot, routed_catalog, events = pipeline._run_gap_hiring(
        outcome,
        request,
        AgencyConfig(),
        object(),
        snapshot,
        [],
        defer_commits=True,
    )

    assert calls == [unit_id]
    assert routed is outcome
    assert routed_snapshot is snapshot
    assert routed_catalog == []
    assert events == [
        {
            "unit_id": unit_id,
            "status": "declined",
            "reason_codes": ["hiring_response_invalid"],
            "case_id": "",
            "worker": "",
            "version": "",
            "notification": "",
            "calls_used": 0,
        }
    ]


def test_activation_canary_rejects_an_inference_team_outside_the_probe_contract(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    request = SimpleNamespace(
        user_message=_task(),
        host="codex",
        capability_status="native-contract-verified",
    )
    for name, value in _CANARY_ENV.items():
        monkeypatch.setenv(name, value)
    routing = _inferred_projection()
    routing["workforce_unit_bindings"][0]["mutation_scope"] = "workspace_write"

    result = pipeline._activation_canary_projection(routing, request)

    assert result["source"] == "workforce_inference_failure"
    assert result["status"] == "inference_invalid"
    assert result["selected_ids"] == []
    assert result["work_units"]["delegate"] is False


def test_activation_canary_rejects_missing_inference_attempt_evidence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    request = SimpleNamespace(
        user_message=_task(),
        host="codex",
        capability_status="native-contract-verified",
    )
    for name, value in _CANARY_ENV.items():
        monkeypatch.setenv(name, value)
    routing = _inferred_projection()
    routing["inference_attempted"] = False

    result = pipeline._activation_canary_projection(routing, request)

    assert result["source"] == "workforce_inference_failure"
    assert result["selected_ids"] == []
    assert "inference_attempted" in result["error"]


def test_activation_canary_rejects_missing_provider_attempt_receipts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    request = SimpleNamespace(
        user_message=_task(),
        host="codex",
        capability_status="native-contract-verified",
    )
    for name, value in _CANARY_ENV.items():
        monkeypatch.setenv(name, value)
    routing = _inferred_projection()
    routing["provider_attempts"] = []

    result = pipeline._activation_canary_projection(routing, request)

    assert result["source"] == "workforce_inference_failure"
    assert result["selected_ids"] == []
    assert "provider_attempts" in result["error"]


def test_ordinary_exact_text_without_restricted_environment_uses_workforce_planner(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from agency_runtime.core.workforce import inference, routing_projection

    clear_cache()
    clear_session_routing()
    monkeypatch.delenv("AGENCY_CANARY_MODE", raising=False)
    monkeypatch.delenv("AGENCY_CANARY_REQUIRE_EXISTING_STORE", raising=False)
    calls: list[str] = []
    planner_options: list[dict[str, Any]] = []

    def fake_planner(message: str, *_args: Any, **_kwargs: Any) -> SimpleNamespace:
        calls.append(message)
        planner_options.append(_kwargs)
        return SimpleNamespace(attempts=())

    monkeypatch.setattr(inference, "plan_and_staff_workforce", fake_planner)
    monkeypatch.setattr(
        pipeline,
        "_run_gap_hiring",
        lambda outcome, request, config, store, snapshot, catalog, **_kwargs: (
            outcome,
            snapshot,
            catalog,
            [],
        ),
    )
    monkeypatch.setattr(
        routing_projection,
        "project_workforce_routing",
        lambda *_args, **_kwargs: {
            "selected_ids": [],
            "semantic_ids": [],
            "confidence": 0.0,
            "status": "abstained",
            "source": "workforce_inference",
            "work_units": {"count": 0, "units": [], "delegate": False},
        },
    )

    result = _route(monkeypatch, set_canary_env=False)

    assert calls == [_task()]
    assert "max_planned_units" not in planner_options[0]
    assert "required_planned_artifact_kind" not in planner_options[0]
    assert result["source"] == "workforce_inference"
