"""A model's name must not decide the request body by accident.

The branch these tests cover picks ``max_completion_tokens`` over ``max_tokens``.
It used to be two independent copies of ``model.startswith("gpt-5")``, and both
disagreed with the model name this package ships: ``config_defaults.yaml`` says
``gpt5.6-luna`` with no hyphen after ``gpt``, so the test answered False for the
family it exists to detect, while an operator config saying ``gpt-5.6-terra``
answered True. The test that covered the branch used ``gpt-5.6`` -- a third
spelling, shipped nowhere -- so nothing was red.

So the load-bearing test here is the one fed from ``config_defaults.yaml``: a
default this package ships can no longer disagree with a branch it takes.
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest
import yaml

from agency_runtime.core import structured_provider
from agency_runtime.core.config import (
    AgencyConfig,
    ProviderEntry,
    _build_provider_entry,
    config_to_yaml,
)
from agency_runtime.core.configuration_contracts import ConfigValidationError
from agency_runtime.core.configuration_schema import _validate_provider, validate_config_document
from agency_runtime.core.model_capabilities import (
    TOKEN_PARAMETER_MAX_COMPLETION_TOKENS,
    TOKEN_PARAMETER_MAX_TOKENS,
    requires_completion_token_parameter,
)
from agency_runtime.core.selector.judge_protocol import encoded_model_payload

_DEFAULTS = Path(__file__).resolve().parents[1] / "agency_runtime" / "core" / "config_defaults.yaml"


def _shipped_models() -> list[str]:
    """Every model name this package ships, wherever it appears."""

    document = yaml.safe_load(_DEFAULTS.read_text(encoding="utf-8"))
    found: list[str] = []

    def walk(node: object) -> None:
        if isinstance(node, dict):
            for key, value in node.items():
                if key == "model" and isinstance(value, str) and value.strip():
                    found.append(value)
                else:
                    walk(value)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk(document)
    return found


def test_the_defaults_file_still_ships_models() -> None:
    """Guards the corpus below from silently emptying and passing vacuously."""

    assert _shipped_models()


def test_no_shipped_model_changes_answer_when_respelled() -> None:
    """Punctuation is not a capability.

    `gpt5.6-luna` and `gpt-5.6-luna` name one family and one API contract. When
    a prefix match decided this, they got different request bodies.
    """

    for model in _shipped_models():
        variants = {
            model,
            model.replace("gpt5", "gpt-5"),
            model.replace("gpt-5", "gpt5"),
            model.replace("-", ""),
            model.upper(),
        }
        answers = {requires_completion_token_parameter(variant) for variant in variants}
        assert len(answers) == 1, f"{model} resolves inconsistently across {sorted(variants)}"


def test_the_shipped_gpt5_default_asks_for_completion_tokens() -> None:
    """The exact regression: this spelling is what `startswith("gpt-5")` missed."""

    assert requires_completion_token_parameter("gpt5.6-luna") is True
    assert requires_completion_token_parameter("gpt5.6-luna-medium") is True
    assert requires_completion_token_parameter("gpt-5.6-terra") is True


@pytest.mark.parametrize("model", ["sonnet", "claude-haiku-4-5", "qwen3.5:2b", "gpt-4o", "GLM-5.2"])
def test_models_outside_the_family_keep_max_tokens(model: str) -> None:
    assert requires_completion_token_parameter(model) is False


@pytest.mark.parametrize(
    ("declared", "expected"),
    [
        (TOKEN_PARAMETER_MAX_COMPLETION_TOKENS, True),
        (TOKEN_PARAMETER_MAX_TOKENS, False),
    ],
)
def test_an_explicit_declaration_overrides_the_name(declared: str, expected: bool) -> None:
    """This is what makes a new model a config edit instead of a code change."""

    # Both directions, against a name that would otherwise decide the opposite.
    assert requires_completion_token_parameter("sonnet", declared=declared) is expected
    assert requires_completion_token_parameter("gpt5.6-luna", declared=declared) is expected


def test_an_unknown_declaration_is_refused_at_config_load() -> None:
    """Ignoring a typo would send the wrong parameter on every single call."""

    with pytest.raises(ValueError, match="token_parameter"):
        _build_provider_entry({"name": "p", "model": "gpt5.6-luna", "token_parameter": "max_token"})


def test_an_absent_declaration_still_loads() -> None:
    entry = _build_provider_entry({"name": "p", "model": "gpt5.6-luna"})

    assert entry.token_parameter == ""


def test_the_rendered_provider_survives_its_own_validator() -> None:
    """The renderer and the schema are two declarations of one shape.

    Adding the field to the dataclass and the renderer without adding it to the
    strict allowlist made every config round trip fail with "effective
    configuration contains an invalid override" -- a message that names neither
    the field nor the file.
    """

    config = replace(
        AgencyConfig(),
        providers=(
            ProviderEntry(
                name="declared",
                type="openai-compatible",
                model="gpt5.6-luna",
                base_url="http://127.0.0.1:4000",
                token_parameter=TOKEN_PARAMETER_MAX_COMPLETION_TOKENS,
            ),
        ),
    )

    rendered = yaml.safe_load(config_to_yaml(config, redact=False))
    validated = validate_config_document(rendered)

    assert validated["providers"][0]["token_parameter"] == TOKEN_PARAMETER_MAX_COMPLETION_TOKENS


def test_the_validator_refuses_an_unknown_declaration() -> None:
    with pytest.raises(ConfigValidationError, match="token_parameter"):
        _validate_provider(
            {
                "name": "p",
                "type": "openai-compatible",
                "model": "gpt5.6-luna",
                "base_url": "http://127.0.0.1:4000",
                "token_parameter": "max_token",
            },
            0,
        )


def test_a_cli_provider_cannot_declare_a_token_parameter() -> None:
    """It builds no HTTP body, so accepting one would be accepting a no-op."""

    with pytest.raises(ConfigValidationError, match="token_parameter"):
        _validate_provider(
            {
                "name": "p",
                "type": "cli",
                "transport": "codex",
                "model": "gpt-5.6-terra",
                "token_parameter": TOKEN_PARAMETER_MAX_COMPLETION_TOKENS,
            },
            0,
        )


def test_the_http_payload_follows_the_declaration() -> None:
    """End to end: the request body the provider actually receives."""

    declared = ProviderEntry(
        name="p",
        type="openai-compatible",
        model="sonnet",
        base_url="https://example.invalid/v1",
        token_parameter=TOKEN_PARAMETER_MAX_COMPLETION_TOKENS,
    )
    payload, _ = structured_provider._http_payload(
        declared, "prompt", {"type": "object"}, system_prompt="system"
    )
    assert "max_completion_tokens" in payload
    assert "temperature" not in payload
    assert "max_tokens" not in payload

    shipped = ProviderEntry(
        name="p",
        type="openai-compatible",
        model="gpt5.6-luna",
        base_url="https://example.invalid/v1",
    )
    payload, _ = structured_provider._http_payload(
        shipped, "prompt", {"type": "object"}, system_prompt="system"
    )
    assert "max_completion_tokens" in payload
    assert "temperature" not in payload


def test_the_judge_payload_agrees_with_the_structured_payload() -> None:
    """Two surfaces, one answer -- the duplication that started this."""

    body = b'{"max_tokens": 256, "temperature": 0}'

    encoded = encoded_model_payload(body, model="gpt5.6-luna", use_completion_tokens=True)
    assert b"max_completion_tokens" in encoded
    assert b"temperature" not in encoded

    # The transport question still wins: an API without the two spellings is
    # never handed the newer one, whatever the model is called.
    encoded = encoded_model_payload(body, model="gpt5.6-luna", use_completion_tokens=False)
    assert b"max_completion_tokens" not in encoded

    encoded = encoded_model_payload(
        body,
        model="sonnet",
        use_completion_tokens=True,
        token_parameter=TOKEN_PARAMETER_MAX_COMPLETION_TOKENS,
    )
    assert b"max_completion_tokens" in encoded
