"""AR-392: a transport failure names its cause instead of collapsing to one code.

Every failure at the transport used to reach the receipt as
``provider_no_valid_response``. ``invoke_structured_provider_result`` returned a
bare ``None`` from eleven places for causes with nothing in common -- a request
that could never be built, a provider unsafe to call, the runtime's own deadline
aborting a call the gateway would have answered, a non-2xx status, a body that
was not JSON, and model text that was not a JSON object -- and the stage loop
stamped one code over all of them.

Two of those causes were separated by hand on 2026-09-04 and had previously been
read as one shape: a call aborted at 30.04 s against the runtime's own 30 s
deadline while the deployment behind the alias allowed 45 s, and a deployment
emitting a misplaced brace (capture391 turn 206: HTTP 200, 5330 characters,
failing at character 257 because a candidate object closed before its ``score``).
Nothing on the receipt told them apart.

These tests pin the replacement contract: the two stage loops classify an
identical failure identically, a non-2xx answer keeps its status, model text that
is not a JSON object is its own cause beside a cut reply, and ``failure_reason``
keeps one meaning -- ``call_attempted`` is what now says whether a call was
spent.
"""

from __future__ import annotations

import json
import urllib.error
from contextlib import nullcontext
from dataclasses import replace
from typing import Any

import pytest

from agency_runtime.core import structured_provider
from agency_runtime.core.config import ProviderEntry
from agency_runtime.core.reply_budget import (
    PROVIDER_CALL_FAILED,
    PROVIDER_CALL_TIMED_OUT,
    PROVIDER_HTTP_STATUS_ERROR,
    PROVIDER_MODEL_TEXT_NOT_JSON,
    PROVIDER_REQUEST_INVALID,
    PROVIDER_RESPONSE_NOT_JSON,
    PROVIDER_RESPONSE_TRUNCATED,
    PROVIDER_UNSAFE_CONFIGURATION,
    TRANSPORT_FAILURE_AFTER_REQUEST,
    TRANSPORT_REFUSAL_BEFORE_REQUEST,
    provider_for_stage,
)
from agency_runtime.core.structured_provider import (
    PROVIDER_CREDENTIAL_ENV_UNSET,
    StructuredProviderResult,
    invoke_structured_provider,
    invoke_structured_provider_result,
)
from agency_runtime.core.workforce import hiring
from agency_runtime.core.workforce.inference import _CallBudget, _invoke_stage

# The runtime's configured deadline for every workforce profile that carries
# ``timeout_ms: 30000``; the deployments behind the aliases allow 45.
_TIMEOUT_SECONDS = 5.0


def _litellm(**overrides: Any) -> ProviderEntry:
    entry = ProviderEntry(
        name="task-agency-recruiter",
        type="litellm",
        model="task-agency-recruiter-v2",
        base_url="http://127.0.0.1:4000",
        timeout=_TIMEOUT_SECONDS,
        reasoning_effort="medium",
    )
    return replace(entry, **overrides)


def _serve_raw(monkeypatch: pytest.MonkeyPatch, raw: bytes | None) -> None:
    monkeypatch.setattr(
        structured_provider, "open_no_redirect", lambda request, *, timeout: nullcontext(object())
    )
    monkeypatch.setattr(
        structured_provider, "_read_http_response", lambda response, *, deadline: raw
    )


def _raise_on_open(monkeypatch: pytest.MonkeyPatch, exc: BaseException) -> None:
    def _open(request: Any, *, timeout: Any) -> Any:
        raise exc

    monkeypatch.setattr(structured_provider, "open_no_redirect", _open)


def _call(provider: ProviderEntry) -> StructuredProviderResult | None:
    return invoke_structured_provider_result(
        provider, "prompt", {"type": "object"}, system_prompt="system"
    )


# --- the runtime's own deadline is not the same thing as a bad reply ----------


def test_the_runtimes_own_deadline_is_named_and_says_the_call_was_made(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # ``_read_http_response`` running past ``deadline`` returns None. That is
    # the 30.04-second abort, and it is the runtime's doing, not the gateway's.
    _serve_raw(monkeypatch, None)

    result = _call(provider_for_stage(_litellm(), "recruiter"))

    assert result is not None
    assert result.carries_no_answer
    assert result.failure_reason == PROVIDER_CALL_TIMED_OUT
    assert result.call_attempted is True
    assert result.value == {}


def test_a_non_2xx_status_is_recorded_instead_of_discarded(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # ``open_no_redirect`` closes the socket-backed body and re-raises the
    # status-bearing exception deliberately. The blanket ``except`` used to
    # throw it away, so a 429, a 401 and a 502 were one code with no status.
    for status in (401, 429, 502):
        with monkeypatch.context() as patch:
            _raise_on_open(
                patch,
                urllib.error.HTTPError(
                    "http://127.0.0.1:4000/v1/chat/completions", status, "no", {}, None  # type: ignore[arg-type]
                ),
            )

            result = _call(provider_for_stage(_litellm(), "recruiter"))

        assert result is not None
        assert result.failure_reason == PROVIDER_HTTP_STATUS_ERROR
        assert result.http_status == status
        assert result.call_attempted is True


def test_a_socket_timeout_reaches_the_same_code_as_the_read_deadline(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _raise_on_open(monkeypatch, TimeoutError("timed out"))
    assert _call(_litellm()).failure_reason == PROVIDER_CALL_TIMED_OUT

    monkeypatch.undo()
    _raise_on_open(monkeypatch, urllib.error.URLError(TimeoutError("timed out")))
    assert _call(_litellm()).failure_reason == PROVIDER_CALL_TIMED_OUT


def test_an_unrecognised_transport_exception_stays_on_the_residual_code(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # The blanket ``except`` stays blanket: nothing escapes the transport, and
    # what it catches without recognising is honestly distinct from the named
    # causes rather than folded into one of them.
    _raise_on_open(monkeypatch, OSError("connection reset by peer"))

    result = _call(_litellm())

    assert result.failure_reason == PROVIDER_CALL_FAILED
    assert result.http_status == 0
    assert result.call_attempted is True


# --- a body that is not JSON, and a body whose model text is not -------------


def test_a_body_that_is_not_a_json_object_is_its_own_cause(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _serve_raw(monkeypatch, b"<html>502 Bad Gateway</html>")

    assert _call(_litellm()).failure_reason == PROVIDER_RESPONSE_NOT_JSON


def test_the_misplaced_brace_from_capture391_turn_206_is_not_a_cut_reply(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # The observed shape: HTTP 200, a complete body, and a candidate object
    # that closes before its ``score``. Nothing was cut at the completion cap,
    # so ``provider_response_truncated`` does not apply and must not be reused.
    misplaced_brace = '{"units": [{"unit_id": "unit-install-operation", "candidates": [{"agent_id": "operations-manager"}, "score": 0.82}]}]}'
    with pytest.raises(json.JSONDecodeError):
        json.loads(misplaced_brace)

    body = {
        "model": "MiniMax-M3",
        "choices": [{"finish_reason": "stop", "message": {"content": misplaced_brace}}],
        # Well below the cap: the reply ended because the model stopped.
        "usage": {"prompt_tokens": 16926, "completion_tokens": 512},
    }
    _serve_raw(monkeypatch, json.dumps(body).encode("utf-8"))

    result = _call(provider_for_stage(_litellm(), "recruiter"))

    assert result.failure_reason == PROVIDER_MODEL_TEXT_NOT_JSON
    assert result.failure_reason != PROVIDER_RESPONSE_TRUNCATED
    assert result.failure_reason != PROVIDER_CALL_TIMED_OUT
    assert result.reply_truncated is False
    assert result.call_attempted is True


# --- failure_reason keeps one meaning; call_attempted carries the other ------


def test_a_refusal_before_any_request_says_no_call_was_made() -> None:
    # Each of these gives up before anything leaves the runtime.
    assert _call(replace(_litellm(), model="")).failure_reason == PROVIDER_UNSAFE_CONFIGURATION
    empty_prompt = invoke_structured_provider_result(
        _litellm(), "   ", {"type": "object"}, system_prompt="system"
    )
    assert empty_prompt.failure_reason == PROVIDER_REQUEST_INVALID

    for result in (_call(replace(_litellm(), model="")), empty_prompt):
        assert result.call_attempted is False
        assert result.failure_reason in TRANSPORT_REFUSAL_BEFORE_REQUEST


def test_the_two_halves_of_the_vocabulary_do_not_overlap() -> None:
    assert not (TRANSPORT_FAILURE_AFTER_REQUEST & TRANSPORT_REFUSAL_BEFORE_REQUEST)
    # ADR-0204's code keeps its original meaning: no call was made.
    assert PROVIDER_CREDENTIAL_ENV_UNSET not in TRANSPORT_FAILURE_AFTER_REQUEST


def test_the_compatibility_wrapper_still_returns_none_for_a_named_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # A named failure carries an empty value. A caller that only asked "is this
    # None?" would otherwise read it as a successful empty answer.
    _serve_raw(monkeypatch, None)

    assert (
        invoke_structured_provider(
            _litellm(), "prompt", {"type": "object"}, system_prompt="system"
        )
        is None
    )


# --- the two stage loops classify the same failure the same way -------------


def _timing_out_invoker(*_args: Any, **_kwargs: Any) -> None:
    """A call that returns nothing after the profile's deadline has passed."""

    return None


def _slow_clock(monkeypatch: pytest.MonkeyPatch, module: Any, elapsed: float) -> None:
    ticks = iter([0.0, elapsed])
    monkeypatch.setattr(module.time, "monotonic", lambda: next(ticks))


def test_the_staffing_loop_splits_a_bare_none_the_way_the_hiring_loop_does(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from agency_runtime.core.workforce import inference as inference_module

    provider = _litellm()
    reached_the_deadline = _TIMEOUT_SECONDS

    with monkeypatch.context() as patch:
        _slow_clock(patch, inference_module, reached_the_deadline)
        _parsed, attempts, failure = _invoke_stage(
            stage="recruiter",
            providers=[provider],
            prompt="p",
            schema={"type": "object"},
            system_prompt="s",
            budget=_CallBudget(1),
            invoker=_timing_out_invoker,
            parser=lambda value: value,
        )

    assert failure == "workforce_inference_failed"
    assert attempts[0].reason_code == PROVIDER_CALL_TIMED_OUT
    assert attempts[0].latency_ms == int(reached_the_deadline * 1000)

    with monkeypatch.context() as patch:
        _slow_clock(patch, hiring, reached_the_deadline)
        _result, _attempt, failures = hiring._invoke(
            [provider],
            prompt="p",
            schema={"type": "object"},
            system="s",
            stage="hire",
            invoker=_timing_out_invoker,
            budget=hiring._CallBudget(1),
        )

    # The same failure, the same code, on both loops.
    assert failures[0].reason_code == PROVIDER_CALL_TIMED_OUT
    assert failures[0].latency_ms == int(reached_the_deadline * 1000)
    assert attempts[0].reason_code == failures[0].reason_code


def test_a_call_that_returned_early_is_a_failed_call_not_a_deadline_abort() -> None:
    _parsed, attempts, _failure = _invoke_stage(
        stage="recruiter",
        providers=[_litellm()],
        prompt="p",
        schema={"type": "object"},
        system_prompt="s",
        budget=_CallBudget(1),
        invoker=_timing_out_invoker,
        parser=lambda value: value,
    )

    assert attempts[0].reason_code == PROVIDER_CALL_FAILED


def test_a_failure_after_the_request_spends_its_call_and_a_refusal_does_not() -> None:
    after = StructuredProviderResult(
        value={},
        provider_name="task-agency-recruiter",
        provider_type="litellm",
        transport="",
        requested_model="task-agency-recruiter-v2",
        model_group="task-agency-recruiter-v2",
        actual_model="",
        model_receipt_source="unavailable",
        latency_ms=0,
        failure_reason=PROVIDER_CALL_TIMED_OUT,
        call_attempted=True,
    )
    before = replace(after, failure_reason=PROVIDER_REQUEST_INVALID, call_attempted=False)

    spent = _CallBudget(4)
    _invoke_stage(
        stage="recruiter",
        providers=[_litellm()],
        prompt="p",
        schema={"type": "object"},
        system_prompt="s",
        budget=spent,
        invoker=lambda *_a, **_k: after,
        parser=lambda value: value,
    )
    assert spent.used == 1

    refunded = _CallBudget(4)
    _invoke_stage(
        stage="recruiter",
        providers=[_litellm()],
        prompt="p",
        schema={"type": "object"},
        system_prompt="s",
        budget=refunded,
        invoker=lambda *_a, **_k: before,
        parser=lambda value: value,
    )
    assert refunded.used == 0


def test_the_hiring_loop_marks_a_refusal_skipped_and_a_failure_failed() -> None:
    before = StructuredProviderResult(
        value={},
        provider_name="task-agency-recruiter",
        provider_type="litellm",
        transport="",
        requested_model="task-agency-recruiter-v2",
        model_group="task-agency-recruiter-v2",
        actual_model="",
        model_receipt_source="unavailable",
        latency_ms=0,
        failure_reason=PROVIDER_CREDENTIAL_ENV_UNSET,
        call_attempted=False,
    )
    budget = hiring._CallBudget(2)

    _result, _attempt, failures = hiring._invoke(
        [_litellm()],
        prompt="p",
        schema={"type": "object"},
        system="s",
        stage="hire",
        invoker=lambda *_a, **_k: before,
        budget=budget,
    )

    assert failures[0].reason_code == PROVIDER_CREDENTIAL_ENV_UNSET
    # "skipped" is already the hiring loop's word for a call it did not make,
    # so the budget count stays the number of calls actually spent.
    assert failures[0].status == "skipped"
    assert budget.used == 0


# --- the operator gets a printed number to compare against ------------------


def test_doctor_states_the_effective_timeout_of_each_routed_profile() -> None:
    """The comparison an operator makes by hand is at least made against a number.

    Which of the two deadlines should be larger is operator configuration, and
    the runtime cannot read the deployment's. Printing its own is what it owes.
    """

    from agency_runtime.core.config import load_config
    from agency_runtime.core.doctor import _routed_inference_profiles, _workforce_timeout_checks

    cfg = load_config()
    profiles = _routed_inference_profiles(cfg)
    checks = _workforce_timeout_checks(cfg)

    if not profiles:
        assert checks == []
        return

    assert len(checks) == 1
    check = checks[0]
    assert check.name == "workforce_profile_timeouts"
    assert check.status == "pass"
    for profile in profiles:
        assert (profile.name or "inference-profile") in check.message
    # The code an aborted call is recorded under is named, so the printed
    # number connects to the receipt an operator would be reading.
    assert PROVIDER_CALL_TIMED_OUT in check.detail
