"""AR-396: a complete reply that is not JSON earns the second ask its siblings get.

``_invoke_stage`` allows two semantic attempts per provider. A reply cut at the
completion cap is asked again naming the cut; a reply that parsed and violated
the contract is asked again through the repair prompts. A reply that arrived
complete and was simply not a JSON object used to end the stage on one call,
because ``structured_provider`` hands it back through the same failure result
as a timeout or an HTTP status error.

It is not that. ``reply_budget`` defines ``PROVIDER_MODEL_TEXT_NOT_JSON`` as the
sibling of a truncated reply -- nothing was cut, the content is simply not what
the schema asked for -- and every workforce route resolves to exactly one
provider profile, so ending the provider ends the stage. Two live staffing turns
on 2026-09-04 died there on a single planner call while the same payload,
replayed ten times with the gateway cache bypassed, answered with valid JSON ten
times out of ten.

These tests pin the split: this one cause retries, every other cause after the
request still ends the provider, and the retry stays inside the same attempt
bound and the same call budget.
"""

from __future__ import annotations

from dataclasses import replace
from typing import Any

import pytest

from agency_runtime.core.config import ProviderEntry
from agency_runtime.core.reply_budget import (
    PROVIDER_CALL_FAILED,
    PROVIDER_CALL_TIMED_OUT,
    PROVIDER_HTTP_STATUS_ERROR,
    PROVIDER_MODEL_TEXT_NOT_JSON,
    PROVIDER_RESPONSE_NOT_JSON,
    TRANSPORT_FAILURE_AFTER_REQUEST,
)
from agency_runtime.core.structured_provider import StructuredProviderResult
from agency_runtime.core.workforce.inference import _CallBudget, _invoke_stage

_TIMEOUT_SECONDS = 5.0


def _litellm(**overrides: Any) -> ProviderEntry:
    entry = ProviderEntry(
        name="task-agency-planner",
        type="litellm",
        model="task-agency-planner-v2",
        base_url="http://127.0.0.1:4000",
        timeout=_TIMEOUT_SECONDS,
        reasoning_effort="medium",
    )
    return replace(entry, **overrides)


def _failed(reason: str) -> StructuredProviderResult:
    """What the transport returns for a cause after the request left."""

    return StructuredProviderResult(
        value={},
        provider_name="task-agency-planner",
        provider_type="litellm",
        transport="",
        requested_model="task-agency-planner-v2",
        model_group="task-agency-planner-v2",
        actual_model="",
        model_receipt_source="unavailable",
        latency_ms=0,
        failure_reason=reason,
        call_attempted=True,
    )


def _applied(value: dict[str, Any]) -> StructuredProviderResult:
    return StructuredProviderResult(
        value=value,
        provider_name="task-agency-planner",
        provider_type="litellm",
        transport="",
        requested_model="task-agency-planner-v2",
        model_group="task-agency-planner-v2",
        actual_model="task-agency-planner-v2",
        model_receipt_source="response.body.model",
        latency_ms=0,
    )


class _Replies:
    """An invoker that answers a scripted sequence and records what it was asked."""

    def __init__(self, *results: StructuredProviderResult) -> None:
        self._results = list(results)
        self.prompts: list[str] = []
        self.system_prompts: list[str] = []

    def __call__(
        self, _provider: ProviderEntry, prompt: str, _schema: Any, *, system_prompt: str, **_kw: Any
    ) -> StructuredProviderResult:
        self.prompts.append(prompt)
        self.system_prompts.append(system_prompt)
        return self._results.pop(0)


def _run(invoker: _Replies, *, budget: int = 4) -> tuple[Any, list[Any], str, _CallBudget]:
    spent = _CallBudget(budget)
    parsed, attempts, failure = _invoke_stage(
        stage="planner",
        providers=[_litellm()],
        prompt="p",
        schema={"type": "object"},
        system_prompt="s",
        budget=spent,
        invoker=invoker,
        parser=lambda value: value,
    )
    return parsed, attempts, failure, spent


def test_a_non_json_reply_is_asked_again_and_the_second_reply_is_applied() -> None:
    invoker = _Replies(_failed(PROVIDER_MODEL_TEXT_NOT_JSON), _applied({"units": []}))

    parsed, attempts, failure, spent = _run(invoker)

    assert parsed == {"units": []}
    assert failure == ""
    assert spent.used == 2
    assert [(item.reason_code, item.status) for item in attempts] == [
        (PROVIDER_MODEL_TEXT_NOT_JSON, "failed"),
        ("structured_response_applied", "applied"),
    ]


def test_the_second_ask_names_the_fault_and_keeps_the_stage_system_prompt() -> None:
    invoker = _Replies(_failed(PROVIDER_MODEL_TEXT_NOT_JSON), _applied({}))

    _run(invoker)

    assert len(invoker.prompts) == 2
    first, second = invoker.prompts
    assert "[RUNTIME VALIDATION FEEDBACK]" not in first
    assert "[RUNTIME VALIDATION FEEDBACK]" in second
    assert second.startswith(first)
    assert '"prior_response_status":"not_json"' in second
    # The reply was not wrong about the task, only about its shape, so the
    # stage keeps its own system prompt rather than switching to a repair one.
    assert invoker.system_prompts == ["s", "s"]


@pytest.mark.parametrize(
    "reason",
    sorted(TRANSPORT_FAILURE_AFTER_REQUEST - {PROVIDER_MODEL_TEXT_NOT_JSON}),
)
def test_every_other_cause_after_the_request_still_ends_the_provider(reason: str) -> None:
    invoker = _Replies(_failed(reason), _applied({"never": "reached"}))

    parsed, attempts, failure, spent = _run(invoker)

    assert parsed is None
    assert failure == "workforce_inference_failed"
    assert spent.used == 1
    assert [(item.reason_code, item.status) for item in attempts] == [(reason, "failed")]


def test_the_retry_is_bounded_by_the_semantic_attempt_allowance() -> None:
    invoker = _Replies(_failed(PROVIDER_MODEL_TEXT_NOT_JSON), _failed(PROVIDER_MODEL_TEXT_NOT_JSON))

    parsed, attempts, failure, spent = _run(invoker)

    assert parsed is None
    assert failure == "workforce_inference_failed"
    assert spent.used == 2
    assert [item.reason_code for item in attempts] == [
        PROVIDER_MODEL_TEXT_NOT_JSON,
        PROVIDER_MODEL_TEXT_NOT_JSON,
    ]


def test_the_retry_never_outruns_the_call_budget() -> None:
    invoker = _Replies(_failed(PROVIDER_MODEL_TEXT_NOT_JSON), _applied({"unreachable": True}))

    parsed, attempts, failure, spent = _run(invoker, budget=1)

    assert parsed is None
    assert failure == "workforce_call_budget_exhausted"
    assert spent.used == 1
    assert [item.reason_code for item in attempts] == [PROVIDER_MODEL_TEXT_NOT_JSON]


def test_the_codes_this_split_is_written_against_are_the_ones_that_exist() -> None:
    # A new code added to one half of the transport split must not silently
    # inherit either behaviour; this is the guard the parametrisation reads.
    assert TRANSPORT_FAILURE_AFTER_REQUEST == {
        PROVIDER_CALL_TIMED_OUT,
        PROVIDER_HTTP_STATUS_ERROR,
        PROVIDER_RESPONSE_NOT_JSON,
        PROVIDER_MODEL_TEXT_NOT_JSON,
        PROVIDER_CALL_FAILED,
    }
