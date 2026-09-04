"""AR-388 / ADR-0204: name the credential the launching environment never carried.

Measured 2026-09-03: every inference profile of the installed runtime reads
``LITELLM_API_KEY`` through ``api_key_env``, nothing on the host exported it,
and every preflight of a Claude session plus two codex activation canaries
failed ``workforce_provider_unavailable`` with zero provider attempts while
the gateway answered. ``_inference_declared`` had asked only the legacy
``providers`` chain and the judge, whose credential is borrowed from that same
variable, so a fully routed install read as undeclared. These cases pin the
replacement: a resolved route is declared inference; a provider whose variable
is unset is recorded as ``provider_credential_env_unset`` before any call; the
outcome, the receipt, the disclosure line and doctor all carry the cause.
"""

from __future__ import annotations

from dataclasses import asdict

import pytest

from agency_runtime.core.config import (
    AgencyConfig,
    InferenceConfig,
    InferenceProfile,
    ProviderEntry,
)
from agency_runtime.core.doctor import _inference_credential_checks
from agency_runtime.core.fail_open_disclosure import (
    MAX_FAIL_OPEN_DISCLOSURE_CHARS,
    render_fail_open_disclosure,
)
from agency_runtime.core.preflight_failure import (
    preflight_staffing_reason_codes,
    project_preflight_provider_attempts,
)
from agency_runtime.core.structured_provider import (
    PROVIDER_CREDENTIAL_ENV_UNSET,
    invoke_structured_provider_result,
    provider_credential_env_unset,
)
from agency_runtime.core.workforce.inference import (
    WORKFORCE_CREDENTIAL_ENV_UNSET,
    _inference_declared,
    plan_and_staff_workforce,
)
from tests.test_workforce_inference import _context, _contract, _snapshot

_VARIABLE = "AGENCY_TEST_GATEWAY_KEY"


def _profile(name: str, model: str, *, adapter: str = "litellm") -> InferenceProfile:
    return InferenceProfile(
        name=name,
        adapter=adapter,
        model=model,
        # A closed loopback port: if the transport ever did call, the connection
        # is refused at once and the attempt reads provider_no_valid_response.
        base_url="http://127.0.0.1:9",
        api_key_env=_VARIABLE,
    )


def _routed_config() -> AgencyConfig:
    """The installed shape: no legacy providers, every stage routed to a profile."""

    return AgencyConfig(
        inference=InferenceConfig(
            routes={
                "workforce.planner": "agency-planner",
                "workforce.recruiter": "agency-recruiter",
            },
            profiles={
                "agency-planner": _profile("agency-planner", "task-agency-planner-v2"),
                "agency-recruiter": _profile("agency-recruiter", "task-agency-recruiter-v2"),
                "unrouted": _profile("unrouted", "spare"),
            },
        )
    )


def test_a_routed_install_is_declared_inference_without_a_legacy_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv(_VARIABLE, raising=False)
    config = _routed_config()

    assert _inference_declared(config, "claude")
    assert not _inference_declared(AgencyConfig(), "claude")


def test_the_transport_refuses_to_call_without_the_variable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv(_VARIABLE, raising=False)
    provider = ProviderEntry(
        name="agency-planner",
        type="litellm",
        model="task-agency-planner-v2",
        base_url="http://127.0.0.1:9",
        api_key_env=_VARIABLE,
    )

    result = invoke_structured_provider_result(
        provider, "plan", {"type": "object"}, system_prompt="planner"
    )

    assert result is not None
    assert result.failure_reason == PROVIDER_CREDENTIAL_ENV_UNSET
    assert result.value == {}
    assert result.model_receipt_source == "unavailable"
    assert result.provider_name == "agency-planner"


def test_the_unset_variable_is_recorded_before_any_call(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv(_VARIABLE, raising=False)
    outcome = plan_and_staff_workforce(
        "Analyze this repository code.",
        _snapshot(_contract("technical-analyst")),
        config=_routed_config(),
        context=_context(),
        invoker=invoke_structured_provider_result,
    )

    assert not outcome.accepted
    assert outcome.status == "inference_unavailable"
    assert outcome.inference_mode == "unavailable"
    assert outcome.calls_used == 0
    assert outcome.plan is None
    assert outcome.proposal is None
    assert [item.reason_code for item in outcome.attempts] == [PROVIDER_CREDENTIAL_ENV_UNSET]
    assert outcome.attempts[0].status == "failed"
    assert outcome.attempts[0].provider_name == "agency-planner"
    assert outcome.attempts[0].stage == "planner"
    assert outcome.abstention_codes == (
        "inference_unavailable",
        "workforce_provider_unavailable",
        WORKFORCE_CREDENTIAL_ENV_UNSET,
    )
    assert [reason.code for reason in outcome.staffing.abstention_reasons] == [
        "inference_unavailable",
        WORKFORCE_CREDENTIAL_ENV_UNSET,
    ]


def test_with_the_variable_set_the_transport_calls_the_provider(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(_VARIABLE, "present")
    outcome = plan_and_staff_workforce(
        "Analyze this repository code.",
        _snapshot(_contract("technical-analyst")),
        config=_routed_config(),
        context=_context(),
        invoker=invoke_structured_provider_result,
    )

    # The closed port refuses the connection the transport now makes, so the
    # attempt is the transport's ordinary failure and the budget was spent.
    assert [item.reason_code for item in outcome.attempts] == ["provider_no_valid_response"]
    assert outcome.calls_used == 1
    assert WORKFORCE_CREDENTIAL_ENV_UNSET not in outcome.abstention_codes


def test_receipt_and_disclosure_name_the_unset_credential(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv(_VARIABLE, raising=False)
    outcome = plan_and_staff_workforce(
        "Analyze this repository code.",
        _snapshot(_contract("technical-analyst")),
        config=_routed_config(),
        context=_context(),
        invoker=invoke_structured_provider_result,
    )

    attempts = project_preflight_provider_attempts([asdict(item) for item in outcome.attempts])
    assert attempts is not None
    assert [(item["stage"], item["reason_code"]) for item in attempts] == [
        ("planner", PROVIDER_CREDENTIAL_ENV_UNSET)
    ]
    codes = preflight_staffing_reason_codes({"workforce_staffing": outcome.staffing.as_dict()})
    assert codes == ["inference_unavailable", WORKFORCE_CREDENTIAL_ENV_UNSET]
    line = render_fail_open_disclosure("workforce_provider_unavailable", codes)
    assert (
        "[Agency staffing failed this turn: workforce_provider_unavailable; "
        "staffing: inference_unavailable, workforce_credential_env_unset]"
    ) in line
    assert len(line) <= MAX_FAIL_OPEN_DISCLOSURE_CHARS


def test_only_a_declared_variable_on_a_keyed_adapter_is_a_credential_fault() -> None:
    keyless_loopback = ProviderEntry(
        name="gateway", type="litellm", model="alias", base_url="http://127.0.0.1:4000"
    )
    direct_key = ProviderEntry(
        name="gateway",
        type="litellm",
        model="alias",
        base_url="http://127.0.0.1:4000",
        api_key="secret",
        api_key_env="UNSET_AGENCY_TEST_VARIABLE",
    )
    cli = ProviderEntry(
        name="codex", type="cli", transport="codex", model="gpt-5", api_key_env=_VARIABLE
    )
    ollama = ProviderEntry(
        name="local",
        type="ollama",
        model="qwen",
        base_url="http://127.0.0.1:11434",
        api_key_env=_VARIABLE,
    )

    assert not provider_credential_env_unset(keyless_loopback)
    assert not provider_credential_env_unset(direct_key)
    assert not provider_credential_env_unset(cli)
    assert not provider_credential_env_unset(ollama)


def test_doctor_names_the_unset_variable_and_the_routed_profiles() -> None:
    config = _routed_config()

    (check,) = _inference_credential_checks(config, environ={})
    assert check.name == "inference_credential_agency_test_gateway_key"
    assert check.status == "warn"
    assert f"{_VARIABLE} is unset in this environment" in check.message
    assert "agency-planner, agency-recruiter" in check.message
    assert "unrouted" not in check.message
    assert "workforce_credential_env_unset" in check.message
    assert f"export {_VARIABLE}" in check.detail

    (present,) = _inference_credential_checks(config, environ={_VARIABLE: "present"})
    assert present.status == "pass"
    assert f"{_VARIABLE} is set in this environment for 2 inference profile(s)" == present.message

    assert _inference_credential_checks(AgencyConfig(), environ={}) == []
