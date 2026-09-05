"""AR-399: a complete JSON object followed by one stray brace is a reply, not prose.

Four planner replies captured on 2026-09-05 were a valid plan object followed by
a single ``}``; the parser read them as not JSON, the second ask drew the same
shape, and the turn ended ``inference_unavailable``. The first complete object
is now accepted when only closing brackets, fence ticks or whitespace follow it,
and the attempt that needed the repair says so.
"""

from __future__ import annotations

from dataclasses import replace
from typing import Any

from agency_runtime.core.config import ProviderEntry
from agency_runtime.core.preflight_failure import _project_validation_reason_codes
from agency_runtime.core.structured_provider import (
    MODEL_TEXT_TRAILING_DATA_TRIMMED,
    StructuredProviderResult,
    _parse_model_text_with_repair,
)
from agency_runtime.core.workforce.inference import _CallBudget, _invoke_stage

_PLAN = '{"request_summary":"Handle a notification.","units":[{"unit_id":"unit-triage","domains":["operations"]}]}'


# --- the parser ----------------------------------------------------------------


def test_one_stray_closing_brace_after_a_complete_object_is_trimmed_and_named() -> None:
    for tail in (" }", "}", "}\n", " } \n", "}}"):
        parsed, repair = _parse_model_text_with_repair(_PLAN + tail)
        assert parsed == {
            "request_summary": "Handle a notification.",
            "units": [{"unit_id": "unit-triage", "domains": ["operations"]}],
        }, tail
        assert repair == MODEL_TEXT_TRAILING_DATA_TRIMMED, tail


def test_the_captured_reply_shapes_parse() -> None:
    # The two tails seen live on 2026-09-05: ``]} }`` and ``]}}\n``.
    for tail in (" }", "}\n"):
        parsed, repair = _parse_model_text_with_repair(_PLAN + tail)
        assert parsed is not None and repair == MODEL_TEXT_TRAILING_DATA_TRIMMED


def test_a_clean_object_needs_no_repair() -> None:
    parsed, repair = _parse_model_text_with_repair(_PLAN)
    assert parsed is not None
    assert repair == ""


def test_a_fenced_object_with_a_stray_brace_is_repaired_too() -> None:
    parsed, repair = _parse_model_text_with_repair("```json\n" + _PLAN + "}\n```")
    assert parsed is not None
    assert repair == MODEL_TEXT_TRAILING_DATA_TRIMMED


def test_a_stray_bracket_followed_by_prose_and_bare_prose_are_still_not_json() -> None:
    # After a stray bracket only closing brackets and whitespace may follow.
    parsed, repair = _parse_model_text_with_repair(_PLAN + "} and that is the plan")
    assert parsed is None
    assert repair == ""
    assert _parse_model_text_with_repair("The plan is to triage it.") == (None, "")
    assert _parse_model_text_with_repair("} {") == (None, "")
    assert _parse_model_text_with_repair(None) == (None, "")


def test_trailing_prose_without_a_stray_bracket_is_accepted_as_before() -> None:
    # Pre-existing behaviour: the first-to-last-brace span already resolved this
    # shape on main, and it carries no repair because that span, not the new
    # path, accepted it.
    assert _parse_model_text_with_repair('{"a":1} and that is the plan') == ({"a": 1}, "")


def test_a_text_without_an_object_is_refused_before_any_decode() -> None:
    assert _parse_model_text_with_repair("[1, 2]}") == (None, "")


def test_a_reply_nested_past_the_recursion_limit_is_not_json_rather_than_an_error() -> None:
    deep = '{"a":' + "[" * 10000 + "]" * 10000 + "}" + "}"
    assert _parse_model_text_with_repair(deep) == (None, "")


# --- the stage loop and the receipt --------------------------------------------


def _litellm() -> ProviderEntry:
    return ProviderEntry(
        name="task-agency-planner",
        type="litellm",
        model="task-agency-planner-v2",
        base_url="http://127.0.0.1:4000",
        timeout=5.0,
    )


def _applied(value: dict[str, Any], *, repair: str = "") -> StructuredProviderResult:
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
        model_text_repair=repair,
    )


class _Replies:
    def __init__(self, *results: StructuredProviderResult) -> None:
        self._results = list(results)

    def __call__(self, _provider: ProviderEntry, _prompt: str, _schema: Any, **_kw: Any) -> Any:
        return self._results.pop(0)


def _run(invoker: _Replies) -> tuple[Any, list[Any], str]:
    return _invoke_stage(
        stage="planner",
        providers=[_litellm()],
        prompt="p",
        schema={"type": "object"},
        system_prompt="s",
        budget=_CallBudget(4),
        invoker=invoker,
        parser=lambda value: value,
    )


def test_a_repaired_reply_is_applied_on_the_first_ask_and_says_it_was_repaired() -> None:
    parsed, attempts, failure = _run(
        _Replies(_applied({"units": []}, repair=MODEL_TEXT_TRAILING_DATA_TRIMMED))
    )

    assert parsed == {"units": []}
    assert failure == ""
    [attempt] = attempts
    assert attempt.status == "applied"
    assert attempt.reason_code == "structured_response_applied"
    assert attempt.validation_reason_codes == (MODEL_TEXT_TRAILING_DATA_TRIMMED,)


def test_a_clean_reply_carries_no_repair_code() -> None:
    _parsed, attempts, _failure = _run(_Replies(_applied({"units": []})))
    [attempt] = attempts
    assert attempt.validation_reason_codes == ()


def test_the_repair_code_survives_receipt_projection_for_every_stage() -> None:
    for stage in ("planner", "subject", "recruiter", "critic", "hiring", "unknown"):
        assert _project_validation_reason_codes(
            [MODEL_TEXT_TRAILING_DATA_TRIMMED], stage=stage
        ) == [MODEL_TEXT_TRAILING_DATA_TRIMMED], stage
    # An unknown code is still refused on a stage with no vocabulary of its own.
    assert _project_validation_reason_codes(["made_up_code"], stage="subject") == []


def test_the_result_field_defaults_to_no_repair() -> None:
    result = _applied({"units": []})
    assert result.model_text_repair == ""
    assert replace(result, model_text_repair="x").model_text_repair == "x"
