"""AR-385 / ADR-0199: the stage owns its reply budget, and a cut reply is named.

``_http_payload`` sent every structured stage on every HTTP provider with
``max_tokens: 2048``, and the gateway spent a thinking-enabled deployment's
reasoning inside that same figure. Captured live on 2026-09-03, four of nine
first recruiter replies stopped at exactly 2048 completion tokens: closed JSON
with the last unit row missing its ``unit_id``, reported with
``finish_reason: stop``. The accumulator raised a plain ``ValueError`` for the
cut row, so the attempt reached the receipt as
``provider_response_contract_invalid`` with nothing attached, and the retry
was told its answer had failed a semantic invariant.

These tests pin the replacement contract: each workforce stage stamps its own
reply budget on the provider it calls, the transport adds the adapter's
thinking allowance so the two no longer share one cap, a reply that reaches
the cap is recorded as ``provider_response_truncated`` with the transport's
own counts on both receipts, the retry is told it was cut, and a cut
nomination row costs only the units it lost.
"""

from __future__ import annotations

import json
from contextlib import nullcontext
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from agency_runtime.core import structured_provider
from agency_runtime.core.config import AgencyConfig, ProviderEntry, WorkforceConfig, load_config
from agency_runtime.core.configuration_contracts import ConfigValidationError
from agency_runtime.core.inference_profiles import provider_from_profile
from agency_runtime.core.preflight_failure import project_preflight_provider_attempts
from agency_runtime.core.reply_budget import (
    DEFAULT_REPLY_BUDGET_TOKENS,
    PROVIDER_RESPONSE_TRUNCATED,
    STAGE_REPLY_BUDGET_TOKENS,
    completion_cap_tokens,
    provider_for_stage,
    stage_reply_budget_tokens,
)
from agency_runtime.core.roster.workforce import WorkforceIndexSnapshot
from agency_runtime.core.selector.receipt_projection import (
    normalize_durable_routing_receipt,
    project_durable_routing_receipt,
    project_reply_truncation,
)
from agency_runtime.core.structured_provider import (
    StructuredProviderResult,
    _http_payload,
    invoke_structured_provider_result,
)
from agency_runtime.core.workforce import hiring
from agency_runtime.core.workforce.contract import (
    WORKFORCE_CONTRACT_SCHEMA_VERSION,
    AuditContract,
    CompositionContract,
    WorkforceContract,
    workforce_index_fingerprint,
)
from agency_runtime.core.workforce.inference import (
    _RECRUITER_REPAIR_SYSTEM,
    _CallBudget,
    _invoke_stage,
    _nomination_repair_feedback_row,
    _NominationAccumulator,
    _NominationValidationError,
    plan_and_staff_workforce,
)
from agency_runtime.core.workforce.planning_contracts import parse_work_unit_plan
from agency_runtime.core.workforce.recruiter_index import (
    project_recruiter_index_record,
    recruiter_index_fingerprint,
    serialize_recruiter_index,
)
from agency_runtime.core.workforce.routing_projection import _provider_attempts
from agency_runtime.core.workforce.staffing_verifier import StaffingContext

_HASH = "sha256:" + "a" * 64
_GENERATION = 7
_INSTALL = "unit-install-operation"
_VERIFY = "unit-verify-install"
_RECRUITER_BUDGET = STAGE_REPLY_BUDGET_TOKENS["recruiter"]


def _litellm(**overrides: Any) -> ProviderEntry:
    entry = ProviderEntry(
        name="task-agency-recruiter",
        type="litellm",
        model="task-agency-recruiter-v2",
        base_url="http://127.0.0.1:4000",
        timeout=5,
        reasoning_effort="medium",
    )
    return replace(entry, **overrides)


def _contract(
    agent_id: str,
    *,
    domains: tuple[str, ...] = ("operations",),
    capabilities: tuple[str, ...] = ("analysis", "planning", "review"),
) -> WorkforceContract:
    return WorkforceContract(
        schema_version=WORKFORCE_CONTRACT_SCHEMA_VERSION,
        worker_id=f"worker:{agent_id}",
        agent_id=agent_id,
        display_name=agent_id.replace("-", " ").title(),
        archetype="planner",
        outcomes=(f"{agent_id} outcome",),
        capability_ids=capabilities,
        artifact_kinds=("plan",),
        lifecycle_phases=("planning",),
        domains=domains,
        stacks=(),
        scope_qualifiers=(),
        not_for=(),
        authority="plan",
        context_mode="isolated_only",
        tool_classes=("repository-read",),
        hosts=("codex", "claude", "openclaw", "hermes"),
        platforms=("windows", "linux"),
        composition=CompositionContract(independence_class=agent_id),
        audit=AuditContract(status="approved", revision="1", contract_valid=True),
        version=_HASH,
        version_hash=_HASH,
        enabled=True,
        employment="employee",
        origin="upstream",
    )


def _snapshot(*contracts: WorkforceContract) -> WorkforceIndexSnapshot:
    records = tuple(project_recruiter_index_record(item) for item in contracts)
    return WorkforceIndexSnapshot(
        generation=_GENERATION,
        worker_count=len(contracts),
        contracts=contracts,
        contract_fingerprint=workforce_index_fingerprint(contracts),
        recruiter_fingerprint=recruiter_index_fingerprint(records),
        recruiter_index=serialize_recruiter_index(records),
    )


def _unit(unit_id: str, outcome: str, domains: list[str]) -> dict[str, Any]:
    return {
        "unit_id": unit_id,
        "outcome": outcome,
        "artifact_kind": "plan",
        "lifecycle_phase": "planning",
        "domains": domains,
        "languages": [],
        "frameworks": [],
        "required_capabilities": ["planning"],
        "authority": "plan",
        "mutation_scope": "read_only",
        "risks": [],
        "trust_boundaries": ["repository"],
        "claims": [],
        "depends_on": [],
        "resources": ["repository"],
        "required_tools": ["repository-read"],
        "platforms": ["linux"],
        "acceptance_evidence": ["The command path and version are recorded."],
        "parallelization": "sequential",
    }


def _plan():
    return parse_work_unit_plan(
        {
            "schema_version": 2,
            "request_summary": "Install the editor and verify the install.",
            "units": [
                _unit(_INSTALL, "Plan the editor install.", ["operations"]),
                _unit(_VERIFY, "Plan the install verification.", ["quality-assurance"]),
            ],
        }
    )


def _context() -> StaffingContext:
    return StaffingContext(
        "codex",
        "linux",
        frozenset({"native-delegation", "repository-read", "shell-execution"}),
        _GENERATION,
    )


def _config(mode: str = "balanced", budget: int = 3) -> AgencyConfig:
    return AgencyConfig(
        providers=(
            ProviderEntry(
                name="task-agency-router",
                type="litellm",
                model="router-alias",
                base_url="https://router.example.test/v1",
                api_key="secret",
                timeout=5,
            ),
        ),
        workforce=WorkforceConfig(mode=mode, balanced_call_budget=budget),
    )


def _nominee(agent_id: str, score: float, classification: str = "required") -> dict[str, Any]:
    return {
        "agent_id": agent_id,
        "score": score,
        "classification": classification,
        "positive_evidence": ["operations-planning-coverage"],
        "negative_evidence": [],
    }


def _row(unit_id: str, agent_id: str) -> dict[str, Any]:
    return {"unit_id": unit_id, "decision": "staff", "ranked_semantic": [_nominee(agent_id, 0.9)]}


def _result(value: dict[str, Any], **overrides: Any) -> StructuredProviderResult:
    result = StructuredProviderResult(
        value=value,
        provider_name="task-agency-router",
        provider_type="litellm",
        transport="",
        requested_model="router-alias",
        model_group="router-alias",
        actual_model="MiniMax-M3",
        model_receipt_source="response.body.model",
        latency_ms=17,
    )
    return replace(result, **overrides)


def _cut(value: dict[str, Any]) -> StructuredProviderResult:
    """The captured shape: closed JSON, ``stop``, and every token of the cap spent."""

    cap = _RECRUITER_BUDGET + 2048
    return _result(
        value,
        reply_budget_tokens=_RECRUITER_BUDGET,
        completion_cap_tokens=cap,
        completion_tokens=cap,
        finish_reason="stop",
        reply_truncated=True,
    )


# --- the budget is the stage's --------------------------------------------


def test_the_recruiter_and_hiring_stages_own_a_budget_the_old_constant_never_gave() -> None:
    for stage in ("recruiter", "hiring", "hiring-repair", "safety_repair"):
        assert stage_reply_budget_tokens(stage) == 16384
    assert all(budget >= 1024 for budget in STAGE_REPLY_BUDGET_TOKENS.values())
    assert stage_reply_budget_tokens("recruiter") > DEFAULT_REPLY_BUDGET_TOKENS
    # An unknown stage is never left at the transport figure either.
    assert stage_reply_budget_tokens("never-heard-of-it") > DEFAULT_REPLY_BUDGET_TOKENS


def test_the_stage_stamps_its_budget_unless_the_operator_stated_one() -> None:
    assert provider_for_stage(_litellm(), "recruiter").reply_budget_tokens == _RECRUITER_BUDGET
    stated = _litellm(reply_budget_tokens=4096)
    assert provider_for_stage(stated, "recruiter") is stated


@pytest.mark.parametrize(
    ("provider", "expected"),
    [
        # litellm forwards the level; the gateway maps medium to a 2048-token
        # thinking budget and caps it at max_tokens - 1, so add exactly that.
        (_litellm(reply_budget_tokens=16384), (16384, 18432)),
        (_litellm(reply_budget_tokens=16384, reasoning_effort="high"), (16384, 20480)),
        (_litellm(reply_budget_tokens=16384, reasoning_effort=""), (16384, 16384)),
        # openai-compatible forwards low/medium/high and drops xhigh.
        (_litellm(type="openai-compatible", reply_budget_tokens=4096), (4096, 6144)),
        (
            _litellm(type="openai-compatible", reply_budget_tokens=4096, reasoning_effort="xhigh"),
            (4096, 4096),
        ),
        # Nothing stamped keeps the historical transport figures.
        (_litellm(reasoning_effort=""), (2048, 2048)),
        (_litellm(type="anthropic"), (8192, 8192)),
        (_litellm(type="ollama", base_url="http://127.0.0.1:11434"), (2048, 2048)),
    ],
)
def test_the_cap_adds_the_thinking_allowance_only_where_the_gateway_shares_it(
    provider: ProviderEntry, expected: tuple[int, int]
) -> None:
    forwarded = structured_provider._forwarded_thinking_level(provider)
    assert completion_cap_tokens(provider, thinking_level_forwarded=forwarded) == expected


def test_the_http_payload_carries_the_stage_cap_not_a_transport_constant() -> None:
    schema = {"type": "object"}
    stamped = provider_for_stage(_litellm(), "recruiter")
    payload, _path = _http_payload(stamped, "prompt", schema, system_prompt="system")
    assert payload["max_tokens"] == _RECRUITER_BUDGET + 2048
    assert payload["reasoning_effort"] == "medium"
    assert "max_completion_tokens" not in payload

    newer, _path = _http_payload(
        replace(stamped, model="gpt-5.6-terra"), "prompt", schema, system_prompt="system"
    )
    assert newer["max_completion_tokens"] == _RECRUITER_BUDGET + 2048
    assert "max_tokens" not in newer

    local, _path = _http_payload(
        replace(stamped, type="ollama", base_url="http://127.0.0.1:11434"),
        "prompt",
        schema,
        system_prompt="system",
    )
    assert local["options"]["num_predict"] == _RECRUITER_BUDGET

    direct, _path = _http_payload(
        replace(stamped, type="anthropic", base_url="https://api.anthropic.test"),
        "prompt",
        schema,
        system_prompt="system",
    )
    assert direct["max_tokens"] == _RECRUITER_BUDGET


# --- the transport names a cut reply -----------------------------------------


def _serve(monkeypatch: pytest.MonkeyPatch, body: dict[str, Any]) -> None:
    raw = json.dumps(body).encode("utf-8")
    monkeypatch.setattr(
        structured_provider, "open_no_redirect", lambda request, *, timeout: nullcontext(object())
    )
    monkeypatch.setattr(
        structured_provider, "_read_http_response", lambda response, *, deadline: raw
    )


def _gateway_reply(content: str, completion_tokens: int, finish_reason: str) -> dict[str, Any]:
    return {
        "model": "MiniMax-M3",
        "choices": [{"finish_reason": finish_reason, "message": {"content": content}}],
        "usage": {"prompt_tokens": 16926, "completion_tokens": completion_tokens},
    }


def test_a_reply_that_spends_exactly_the_cap_is_truncated_even_when_the_gateway_says_stop(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider = provider_for_stage(_litellm(), "recruiter")
    cap = _RECRUITER_BUDGET + 2048
    _serve(monkeypatch, _gateway_reply('{"units": [{"decision": "staff"}]}', cap, "stop"))

    result = invoke_structured_provider_result(
        provider, "prompt", {"type": "object"}, system_prompt="system"
    )

    assert result is not None
    assert result.value == {"units": [{"decision": "staff"}]}
    assert result.reply_truncated
    assert (result.reply_budget_tokens, result.completion_cap_tokens) == (_RECRUITER_BUDGET, cap)
    assert (result.completion_tokens, result.finish_reason) == (cap, "stop")
    assert result.receipt()["reply_truncated"] is True


@pytest.mark.parametrize(
    ("completion_tokens", "finish_reason", "truncated"),
    [(992, "stop", False), (992, "length", True), (18432, "stop", True), (18433, "stop", True)],
)
def test_the_provider_is_believed_when_it_says_length_and_checked_when_it_says_stop(
    monkeypatch: pytest.MonkeyPatch,
    completion_tokens: int,
    finish_reason: str,
    truncated: bool,
) -> None:
    provider = provider_for_stage(_litellm(), "recruiter")
    _serve(monkeypatch, _gateway_reply('{"units": []}', completion_tokens, finish_reason))

    result = invoke_structured_provider_result(
        provider, "prompt", {"type": "object"}, system_prompt="system"
    )

    assert result is not None
    assert result.reply_truncated is truncated
    assert result.completion_tokens == completion_tokens


def test_a_cut_reply_with_no_json_object_returns_the_truncation_instead_of_none(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider = provider_for_stage(_litellm(), "recruiter")
    unclosed = '{"units": [{"unit_id": "unit-install-operation", "decision": "staff"'
    _serve(monkeypatch, _gateway_reply(unclosed, _RECRUITER_BUDGET + 2048, "stop"))
    cut = invoke_structured_provider_result(
        provider, "prompt", {"type": "object"}, system_prompt="s"
    )
    assert cut is not None
    assert cut.value == {}
    assert cut.reply_truncated

    # The same unreadable text below the cap is still no response at all.
    _serve(monkeypatch, _gateway_reply(unclosed, 500, "stop"))
    assert (
        invoke_structured_provider_result(provider, "prompt", {"type": "object"}, system_prompt="s")
        is None
    )


def test_a_reply_without_usage_is_never_called_truncated(monkeypatch: pytest.MonkeyPatch) -> None:
    provider = provider_for_stage(_litellm(), "recruiter")
    body = {"model": "m", "choices": [{"message": {"content": '{"units": []}'}}]}
    _serve(monkeypatch, body)

    result = invoke_structured_provider_result(
        provider, "prompt", {"type": "object"}, system_prompt="s"
    )

    assert result is not None
    assert result.completion_tokens is None
    assert result.reply_truncated is False


# --- the stage records the cut and tells the retry -----------------------------


def test_the_stage_records_a_cut_reply_as_truncated_and_names_the_cut_on_the_retry() -> None:
    seen: list[tuple[ProviderEntry, str, str]] = []
    replies = iter((_cut({"units": [{"decision": "staff"}]}), _result({"units": "complete"})))

    def invoke(provider, prompt, _schema, *, system_prompt, timeout):
        seen.append((provider, prompt, system_prompt))
        return next(replies)

    def parse(value):
        if value != {"units": "complete"}:
            raise ValueError("workforce nomination row is invalid")
        return value

    parsed, attempts, failure = _invoke_stage(
        stage="recruiter",
        providers=[_litellm()],
        prompt="the prompt",
        schema={"type": "object"},
        system_prompt="the system prompt",
        budget=_CallBudget(3),
        invoker=invoke,
        parser=parse,
        repair_system_prompt=_RECRUITER_REPAIR_SYSTEM,
    )

    assert (parsed, failure) == ({"units": "complete"}, "")
    assert [item.reason_code for item in attempts] == [
        PROVIDER_RESPONSE_TRUNCATED,
        "structured_response_applied",
    ]
    first = attempts[0]
    assert first.status == "rejected"
    assert first.reply_truncated
    assert (first.reply_budget_tokens, first.completion_cap_tokens, first.completion_tokens) == (
        _RECRUITER_BUDGET,
        _RECRUITER_BUDGET + 2048,
        _RECRUITER_BUDGET + 2048,
    )
    # The stamped budget reached the invoker on both calls.
    assert [provider.reply_budget_tokens for provider, _, _ in seen] == [_RECRUITER_BUDGET] * 2
    # A plain ValueError takes the generic retry, which now also names the cut.
    retry_prompt = seen[1][1]
    assert retry_prompt.startswith("the prompt\n\n[RUNTIME VALIDATION FEEDBACK]\n")
    assert "cut off at the completion cap" in retry_prompt
    assert f'"completion_tokens":{_RECRUITER_BUDGET + 2048}' in retry_prompt
    assert seen[1][2] == "the system prompt"


def test_a_cut_reply_with_nothing_to_parse_is_recorded_without_calling_the_parser() -> None:
    prompts: list[str] = []
    parsed_values: list[Any] = []
    replies = iter((_cut({}), _result({"ok": True})))

    def invoke(_provider, prompt, _schema, **_kwargs):
        prompts.append(prompt)
        return next(replies)

    def parse(value):
        parsed_values.append(value)
        return value

    parsed, attempts, _failure = _invoke_stage(
        stage="critic",
        providers=[_litellm()],
        prompt="critic prompt",
        schema={"type": "object"},
        system_prompt="critic system",
        budget=_CallBudget(2),
        invoker=invoke,
        parser=parse,
    )

    assert parsed == {"ok": True}
    assert parsed_values == [{"ok": True}]
    assert attempts[0].reason_code == PROVIDER_RESPONSE_TRUNCATED
    assert attempts[0].validation_detail == "structured reply was cut at the completion cap"
    feedback = json.loads(prompts[1].split("[RUNTIME VALIDATION FEEDBACK]\n", 1)[1])
    assert feedback["prior_response_status"] == "truncated"
    assert feedback["reply_truncation"]["completion_cap_tokens"] == _RECRUITER_BUDGET + 2048


def test_a_reply_that_validates_is_applied_whatever_the_provider_reports() -> None:
    parsed, attempts, _failure = _invoke_stage(
        stage="recruiter",
        providers=[_litellm()],
        prompt="p",
        schema={"type": "object"},
        system_prompt="s",
        budget=_CallBudget(1),
        invoker=lambda *_args, **_kwargs: _cut({"units": "complete"}),
        parser=lambda value: value,
    )

    assert parsed == {"units": "complete"}
    assert attempts[0].status == "applied"
    assert attempts[0].reply_truncated  # the transport fact is kept, honestly


def test_a_no_response_attempt_still_carries_the_stamped_budget() -> None:
    _parsed, attempts, failure = _invoke_stage(
        stage="planner",
        providers=[_litellm()],
        prompt="p",
        schema={"type": "object"},
        system_prompt="s",
        budget=_CallBudget(1),
        invoker=lambda *_args, **_kwargs: None,
        parser=lambda value: value,
    )

    assert failure == "workforce_inference_failed"
    assert attempts[0].reason_code == "provider_no_valid_response"
    assert attempts[0].reply_budget_tokens == STAGE_REPLY_BUDGET_TOKENS["planner"]
    assert attempts[0].reply_truncated is False


# --- a cut nomination costs only the units it lost ----------------------------


def _accumulator() -> _NominationAccumulator:
    return _NominationAccumulator(
        _plan(),
        _snapshot(
            _contract("operations-manager"),
            _contract("qa-planner", domains=("quality-assurance", "operations")),
        ),
        config=_config(),
        context=_context(),
        allowed_candidate_ids=frozenset({"operations-manager", "qa-planner"}),
    )


def test_a_row_cut_mid_way_loses_only_its_own_unit_and_the_repair_completes_it() -> None:
    parser = _accumulator()
    cut_row = {"unit_id": _VERIFY, "decision": "staff"}  # ranked_semantic never arrived

    with pytest.raises(_NominationValidationError) as cut:
        parser.parse({"units": [_row(_INSTALL, "operations-manager"), cut_row]})

    (failure,) = cut.value.failures
    assert (failure.unit_id, failure.code) == (_VERIFY, "missing_work_unit")
    assert failure.diagnostic_code == "recruiter_unit_row_shape_invalid"
    assert str(cut.value) == f"workforce nomination failures: {_VERIFY}=missing_work_unit"

    proposal = parser.parse({"units": [_row(_VERIFY, "qa-planner")]})

    assert [unit.selected for unit in proposal.units] == [("operations-manager",), ("qa-planner",)]


def test_a_row_cut_before_its_unit_id_leaves_that_unit_missing_without_a_diagnosis() -> None:
    parser = _accumulator()
    nameless = {"decision": "staff", "ranked_semantic": [_nominee("qa-planner", 0.9)]}

    with pytest.raises(_NominationValidationError) as cut:
        parser.parse({"units": [_row(_INSTALL, "operations-manager"), nameless]})

    (failure,) = cut.value.failures
    assert (failure.unit_id, failure.code, failure.diagnostic_code) == (
        _VERIFY,
        "missing_work_unit",
        "",
    )


def test_a_repair_cut_short_leaves_the_unit_missing_again_and_still_refuses_extra_units() -> None:
    parser = _accumulator()
    with pytest.raises(_NominationValidationError):
        parser.parse({"units": [_row(_INSTALL, "operations-manager")]})

    with pytest.raises(_NominationValidationError) as again:
        parser.parse({"units": [{"unit_id": _VERIFY, "decision": "staff"}]})
    assert [item.unit_id for item in again.value.failures] == [_VERIFY]

    with pytest.raises(_NominationValidationError, match="missing_work_unit"):
        parser.parse({"units": [_row(_INSTALL, "operations-manager"), _row(_VERIFY, "qa-planner")]})


def test_the_repair_feedback_says_the_row_could_not_be_read() -> None:
    parser = _accumulator()
    with pytest.raises(_NominationValidationError) as cut:
        parser.parse({"units": [_row(_INSTALL, "operations-manager"), {"unit_id": _VERIFY}]})

    row = _nomination_repair_feedback_row(cut.value.failures[0])

    assert row["diagnostic_code"] == "recruiter_unit_row_shape_invalid"
    assert "could not be read" in row["required_correction"]
    assert "Return the missing planned-unit row." in row["required_correction"]


def test_a_whole_reply_the_runtime_cannot_read_is_still_refused_outright() -> None:
    parser = _accumulator()
    for hostile in ({}, {"units": []}, {"units": "rows"}, {"units": [{}, {}, {}]}):
        with pytest.raises(ValueError):
            parser.parse(hostile)


# --- both receipts carry the record ---------------------------------------------


def _attempt(**overrides: Any) -> dict[str, Any]:
    attempt = {
        "stage": "recruiter",
        "provider_name": "task-agency-recruiter",
        "provider_type": "litellm",
        "requested_model": "task-agency-recruiter-v2",
        "model_group": "task-agency-recruiter-v2",
        "actual_model": "MiniMax-M3",
        "model_receipt_source": "response.body.model",
        "status": "rejected",
        "reason_code": PROVIDER_RESPONSE_TRUNCATED,
        "reason": PROVIDER_RESPONSE_TRUNCATED,
        "validation_detail": f"workforce nomination failures: {_VERIFY}=missing_work_unit",
        "validation_reason_codes": ["recruiter_unit_row_shape_invalid"],
        "reply_budget_tokens": 16384,
        "completion_cap_tokens": 18432,
        "completion_tokens": 18432,
        "reply_truncated": True,
    }
    attempt.update(overrides)
    return attempt


def test_the_preflight_failure_receipt_is_never_blank_on_a_cut_reply() -> None:
    (entry,) = project_preflight_provider_attempts([_attempt()]) or [None]

    assert entry is not None
    assert entry["reason_code"] == PROVIDER_RESPONSE_TRUNCATED
    assert entry["truncation"] == {
        "reply_budget_tokens": 16384,
        "completion_cap_tokens": 18432,
        "completion_tokens": 18432,
    }
    assert entry["validation_failures"] == [
        {"unit_id": _VERIFY, "reason_code": "missing_work_unit"}
    ]
    assert entry["validation_reason_codes"] == ["recruiter_unit_row_shape_invalid"]


@pytest.mark.parametrize(
    "overrides",
    [
        {"reply_truncated": False},
        {"reply_truncated": "yes"},
        {"reply_truncated": 1},
        {"reply_truncated": None},
    ],
)
def test_only_a_true_truncation_flag_produces_the_record(overrides: dict[str, Any]) -> None:
    (entry,) = project_preflight_provider_attempts([_attempt(**overrides)]) or [None]

    assert entry is not None
    assert "truncation" not in entry


def test_the_truncation_counts_are_bounded_and_content_free() -> None:
    hostile = _attempt(
        reply_budget_tokens=True,
        completion_cap_tokens=-5,
        completion_tokens=10**12,
    )

    assert project_reply_truncation(hostile) == {
        "reply_budget_tokens": 0,
        "completion_cap_tokens": 0,
        "completion_tokens": 1_048_576,
    }
    assert project_reply_truncation({"completion_tokens": 5}) is None
    assert project_reply_truncation("truncated") is None


def test_the_routing_receipt_carries_the_record_and_round_trips_it() -> None:
    routing = {
        "trace_id": "trace-cut-reply",
        "query_hash": "a" * 64,
        "context_fingerprint": "c" * 64,
        "selected_ids": [],
        "semantic_ids": [],
        "confidence": 0.0,
        "top_score": 0.0,
        "latency_ms": 17,
        "candidate_count": 2,
        "status": "inference_invalid",
        "source": "inference",
        "inference_configured": True,
        "inference_required": True,
        "inference_attempted": True,
        "inference_mode": "invalid",
        "provider_attempts": [
            _attempt(),
            _attempt(
                reason_code="structured_response_applied",
                reason="structured_response_applied",
                status="applied",
                reply_truncated=False,
            ),
        ],
    }

    receipt = project_durable_routing_receipt(routing)

    cut, applied = receipt["inference"]["provider_attempts"]
    assert cut["reason_code"] == PROVIDER_RESPONSE_TRUNCATED
    assert cut["truncation"] == {
        "reply_budget_tokens": 16384,
        "completion_cap_tokens": 18432,
        "completion_tokens": 18432,
    }
    assert "truncation" not in applied
    assert normalize_durable_routing_receipt(receipt) == receipt


def test_the_routing_projection_carries_the_transport_accounting() -> None:
    _parsed, attempts, _failure = _invoke_stage(
        stage="recruiter",
        providers=[_litellm()],
        prompt="p",
        schema={"type": "object"},
        system_prompt="s",
        budget=_CallBudget(1),
        invoker=lambda *_args, **_kwargs: _cut({}),
        parser=lambda value: value,
    )

    (projected,) = _provider_attempts(SimpleNamespace(attempts=attempts))

    assert projected["reason"] == PROVIDER_RESPONSE_TRUNCATED
    assert projected["reply_truncated"] is True
    assert (projected["reply_budget_tokens"], projected["completion_cap_tokens"]) == (
        _RECRUITER_BUDGET,
        _RECRUITER_BUDGET + 2048,
    )


# --- the operator may state a budget --------------------------------------------


def _write(path: Path, text: str) -> Path:
    path.write_text(text)
    path.chmod(0o600)
    return path


def test_a_stated_profile_or_provider_budget_reaches_the_transport(tmp_path: Path) -> None:
    path = _write(
        tmp_path / "agency.yaml",
        "inference:\n"
        "  routes:\n"
        "    workforce.recruiter: big\n"
        "  profiles:\n"
        "    big:\n"
        "      adapter: litellm\n"
        "      model: task-x\n"
        "      base_url: http://127.0.0.1:4000\n"
        "      thinking_level: medium\n"
        "      reply_budget_tokens: 4096\n"
        "providers:\n"
        "  - name: legacy\n"
        "    type: litellm\n"
        "    model: task-y\n"
        "    base_url: http://127.0.0.1:4000\n"
        "    reply_budget_tokens: 8192\n",
    )
    loaded = load_config(path, reload=True)

    profile = loaded.inference.profiles["big"]
    assert profile.reply_budget_tokens == 4096
    stamped = provider_for_stage(provider_from_profile(profile), "recruiter")
    assert stamped.reply_budget_tokens == 4096
    assert completion_cap_tokens(stamped, thinking_level_forwarded="medium") == (4096, 6144)
    assert [entry.reply_budget_tokens for entry in loaded.providers] == [8192]


@pytest.mark.parametrize("budget", ["100", "-1", "1000000", "true", "'lots'"])
def test_a_budget_the_transport_cannot_honour_is_refused_at_load(
    tmp_path: Path, budget: str
) -> None:
    path = _write(
        tmp_path / "agency.yaml",
        "inference:\n"
        "  profiles:\n"
        "    tiny:\n"
        "      adapter: litellm\n"
        "      model: task-x\n"
        "      base_url: http://127.0.0.1:4000\n"
        f"      reply_budget_tokens: {budget}\n",
    )

    with pytest.raises(ConfigValidationError, match="reply_budget_tokens"):
        load_config(path, reload=True)


# --- hiring ---------------------------------------------------------------------


def test_hiring_stamps_its_budget_and_records_a_cut_reply_as_its_own_class() -> None:
    seen: list[ProviderEntry] = []

    def invoke(provider, _prompt, _schema, **_kwargs):
        seen.append(provider)
        return _cut({})

    result, attempt, failures = hiring._invoke(
        [_litellm(name="hiring-a"), _litellm(name="hiring-b")],
        prompt="hire",
        schema={"type": "object"},
        system="hire system",
        stage="hiring",
        invoker=invoke,
        budget=hiring._CallBudget(4),
    )

    assert (result, attempt) == (None, None)
    assert [item.reply_budget_tokens for item in seen] == [16384, 16384]
    assert [item.reason_code for item in failures] == [PROVIDER_RESPONSE_TRUNCATED] * 2
    assert {item.status for item in failures} == {"failed"}


# --- end to end -------------------------------------------------------------------


def test_a_cut_first_nomination_is_repaired_from_the_units_it_lost() -> None:
    snapshot = _snapshot(
        _contract("operations-manager"),
        _contract("qa-planner", domains=("quality-assurance", "operations")),
    )
    plan = {
        "request_summary": "Install the editor and verify the install.",
        "units": [
            {
                "unit_id": _INSTALL,
                "outcome": "Plan the editor install.",
                "artifact_kind": "plan",
                "domains": ["operations"],
                "stacks": [],
                "capability_ids": ["planning"],
                "novel_capability": "",
                "depends_on": [],
            },
            {
                "unit_id": _VERIFY,
                "outcome": "Plan the install verification.",
                "artifact_kind": "plan",
                "domains": ["quality-assurance"],
                "stacks": [],
                "capability_ids": ["planning"],
                "novel_capability": "",
                "depends_on": [_INSTALL],
            },
        ],
    }
    first = {
        "units": [_row(_INSTALL, "operations-manager"), {"unit_id": _VERIFY, "decision": "staff"}]
    }
    repair = {"units": [_row(_VERIFY, "qa-planner")]}
    replies = iter((_result(plan), _cut(first), _result(repair)))
    calls: list[tuple[str, str]] = []

    def invoke(_provider, prompt, _schema, *, system_prompt, **_kwargs):
        calls.append((prompt, system_prompt))
        return next(replies)

    outcome = plan_and_staff_workforce(
        "Install the editor and verify the install.",
        snapshot,
        config=_config(),
        context=_context(),
        invoker=invoke,
    )

    assert outcome.accepted
    assert [(item.stage, item.status, item.reason_code) for item in outcome.attempts] == [
        ("planner", "applied", "structured_response_applied"),
        ("recruiter", "rejected", PROVIDER_RESPONSE_TRUNCATED),
        ("recruiter", "applied", "structured_response_applied"),
    ]
    assert outcome.attempts[1].validation_reason_codes == ("recruiter_unit_row_shape_invalid",)
    assert [unit.selected for unit in outcome.staffing.units] == [
        ("operations-manager",),
        ("qa-planner",),
    ]
    repair_prompt, repair_system = calls[2]
    assert repair_system == _RECRUITER_REPAIR_SYSTEM
    feedback = json.loads(repair_prompt.split("[RUNTIME VALIDATION FEEDBACK]\n", 1)[1])
    assert [row["unit_id"] for row in feedback["failed_units"]] == [_VERIFY]
    assert feedback["reply_truncation"]["completion_tokens"] == _RECRUITER_BUDGET + 2048
    assert "cut off at the completion cap" in feedback["reply_truncation"]["required_action"]
