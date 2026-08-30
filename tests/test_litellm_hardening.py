"""Adversarial coverage for the optional LiteLLM integration boundary."""

from __future__ import annotations

import asyncio
import sqlite3
import threading
from copy import deepcopy
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

import agency_runtime.adapters.litellm.callback as callback_module
from agency_runtime.adapters.litellm.callback import (
    AgencyLiteLLMCallback,
    LiteLLMAdapter,
    litellm_health_check,
    register_litellm_callback,
)
from agency_runtime.adapters.litellm.evidence import (
    bounded,
    bounded_count,
    clean,
    event_identity,
    first,
    hidden_params,
    identifier,
    iso_time,
    known_headers,
    mapping,
    metadata,
    provider_model,
    response_value,
    sanitize_api_base,
    session_id,
    trace_id,
)
from agency_runtime.adapters.litellm.request_context import (
    AGENCY_PREFLIGHT_MARKER,
    MAX_CAPTURE_CHARS,
    MAX_ROUTING_INPUT_CHARS,
    content_text,
    inject_message_context,
    inject_proxy_context,
    proxy_request_input,
    redact_content,
    user_message,
)
from agency_runtime.core.config import AgencyConfig, ObservabilityConfig
from agency_runtime.core.config_binding import StoreConfigBindingError
from agency_runtime.core.configuration import apply_config_operations, read_config_state
from agency_runtime.core.selector.pipeline import HEADER_INSTRUCTION
from agency_runtime.core.store.sqlite import Store


def _config(
    *,
    enabled: str = "auto",
    skip_models: tuple[str, ...] | None = None,
    capture_content: bool = False,
) -> AgencyConfig:
    base = AgencyConfig()
    adapter = replace(
        base.adapters.litellm,
        enabled=enabled,
        skip_models=(base.adapters.litellm.skip_models if skip_models is None else skip_models),
    )
    return replace(
        base,
        adapters=replace(base.adapters, litellm=adapter),
        observability=ObservabilityConfig(
            capture_content=capture_content,
            retention_days=30,
        ),
    )


def _managed_context(source: str) -> str:
    """Return the exact legacy Agency context shape owned by the adapter."""

    return (
        f"{AGENCY_PREFLIGHT_MARKER} Specialist routing suggestion "
        f"(confidence=1.0, source={source}): code-reviewer\n"
        f"{HEADER_INSTRUCTION}"
    )


class _HealthResponse:
    def __init__(self, status: int) -> None:
        self.status = status

    def __enter__(self) -> _HealthResponse:
        return self

    def __exit__(self, *_: Any) -> None:
        return None


def test_health_check_is_bounded_no_redirect_and_rejects_unsafe_urls(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    opened: list[tuple[str, float, str]] = []

    def open_ok(request: Any, *, timeout: float) -> _HealthResponse:
        opened.append((request.full_url, timeout, request.get_method()))
        return _HealthResponse(200)

    monkeypatch.setattr(callback_module, "open_no_redirect", open_ok)
    assert litellm_health_check(config=AgencyConfig()) is True
    assert opened == [("http://127.0.0.1:4000/health/liveness", 2, "GET")]

    opened.clear()
    assert litellm_health_check("http://example.com:4000") is False
    assert opened == []

    monkeypatch.setattr(
        callback_module,
        "open_no_redirect",
        lambda *_args, **_kwargs: _HealthResponse(204),
    )
    assert litellm_health_check("https://gateway.example/v1/") is False

    def unavailable(*_args: Any, **_kwargs: Any) -> Any:
        raise OSError("offline")

    monkeypatch.setattr(callback_module, "open_no_redirect", unavailable)
    assert litellm_health_check("https://gateway.example") is False


def test_evidence_ids_cover_supported_litellm_payload_shapes_and_are_bounded() -> None:
    oversized = "x" * 400
    assert clean(None) == ""
    assert bounded(f" {oversized} ", 8) == "x" * 8
    assert mapping(None) == {}
    assert first(None, " ", "chosen") == "chosen"
    assert first(None, " ") == ""

    payload = {
        "metadata": {"agency_trace_id": oversized, "session_id": "direct-session"},
        "litellm_params": {
            "metadata": {
                "agency_trace_id": "nested-loses",
                "agency_session_id": "nested-session",
            }
        },
    }
    assert metadata(payload)["agency_trace_id"] == oversized
    bounded_trace = trace_id(payload)
    assert len(bounded_trace) == 256
    assert bounded_trace.startswith("x" * 200)
    assert bounded_trace == identifier(oversized)
    assert bounded_trace != "x" * 256
    assert session_id(payload, "fallback") == "nested-session"

    candidates = [
        ({"metadata": {"trace_id": "metadata-trace"}}, "metadata-trace"),
        ({"litellm_call_id": "call-id"}, "call-id"),
        ({"litellm_params": {"litellm_call_id": "nested-call"}}, "nested-call"),
        ({"litellm_trace_id": "trace-field"}, "trace-field"),
        ({"litellm_params": {"litellm_trace_id": "nested-trace"}}, "nested-trace"),
    ]
    for candidate, expected in candidates:
        assert trace_id(candidate) == expected
    assert trace_id({}, {"id": "response-id"}) == "response-id"
    assert session_id({"session_id": "payload-session"}, "fallback") == "payload-session"
    assert session_id({}, "fallback") == "fallback"


def test_response_and_header_evidence_filters_arbitrary_or_broken_containers() -> None:
    class BrokenHeaders:
        def items(self) -> Any:
            raise RuntimeError("untrusted header container")

    response = SimpleNamespace(
        id="attribute-id",
        _hidden_params={
            "additional_headers": BrokenHeaders(),
            "model_group": "direct-group",
            "attempted_fallbacks": 4,
        },
        _response=SimpleNamespace(
            headers={
                "X-LiteLLM-Model-Api-Base": "https://api.example/v1",
                "X-LiteLLM-Model-Id": "m" * 5000,
                "Authorization": "Bearer do-not-copy",
                None: "ignored",
                "x-litellm-model-group": None,
            }
        ),
    )
    assert response_value({"id": "mapping-id"}, "id") == "mapping-id"
    assert response_value(response, "id") == "attribute-id"
    assert hidden_params(object()) == {}

    headers = known_headers(response)
    assert headers["x-litellm-model-group"] == "direct-group"
    assert headers["x-litellm-model-api-base"] == "https://api.example/v1"
    assert headers["x-litellm-attempted-fallbacks"] == "4"
    assert len(headers["x-litellm-model-id"]) == 4096
    assert "authorization" not in headers

    unsupported = {"_hidden_params": {"additional_headers": object()}}
    assert known_headers(unsupported) == {}


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (None, ""),
        ("file://host/private", ""),
        ("https:///missing-host", ""),
        ("https://host:invalid/path", ""),
        ("https://host/path with space", ""),
        ("https://host/path\nnext", ""),
        (
            "HTTPS://user:pass@[2001:DB8::1]:443/v1/?token=secret#fragment",
            "https://[2001:db8::1]:443/v1",
        ),
        ("http://EXAMPLE.test:8080/v1/", "http://example.test:8080/v1"),
    ],
)
def test_api_base_sanitization_is_credential_safe(value: Any, expected: str) -> None:
    assert sanitize_api_base(value) == expected


@pytest.mark.parametrize(
    ("model", "expected"),
    [
        (None, ("", "")),
        ("custom/alias", ("", "")),
        ("gpt-5", ("", "gpt-5")),
        ("openai/gpt-5", ("openai", "gpt-5")),
        ("/broken", ("", "")),
        ("provider/", ("", "")),
    ],
)
def test_provider_model_never_promotes_custom_or_malformed_aliases(
    model: Any,
    expected: tuple[str, str],
) -> None:
    assert provider_model(model) == expected


def test_time_identity_and_count_coercion_are_stable_and_bounded() -> None:
    naive = datetime(2026, 7, 12, 12, 0)
    offset = datetime(2026, 7, 12, 8, 0, tzinfo=timezone(timedelta(hours=-4)))
    assert iso_time(naive) == "2026-07-12T12:00:00+00:00"
    assert iso_time(offset) == "2026-07-12T12:00:00+00:00"
    assert iso_time("2026-07-12T12:00:00Z") == "2026-07-12T12:00:00+00:00"
    assert datetime.fromisoformat(iso_time(None)).tzinfo is not None
    assert datetime.fromisoformat(iso_time("not-a-time")).tzinfo is not None

    response = {"id": "response-id"}
    assert event_identity(response, None) == "response-id"
    assert len(event_identity({"id": "r" * 400}, None)) == 256
    assert event_identity({}, naive) == "2026-07-12T12:00:00+00:00"
    assert event_identity({}, "stable-start") == "stable-start"
    no_identity: dict[str, Any] = {}
    assert event_identity(no_identity, None) == str(id(no_identity))

    assert bounded_count(True) == 0
    assert bounded_count(object()) == 0
    assert bounded_count("invalid") == 0
    assert bounded_count(-4) == 0
    assert bounded_count("3") == 3
    assert bounded_count(50_000) == 10_000
    assert bounded_count(50, maximum=20) == 20


def test_opt_in_redaction_handles_structured_and_common_credentials() -> None:
    source = (
        'email=user@example.com "api_key":"plain-secret" '
        "password='correct horse battery staple' "
        "Authorization: Bearer abcdefghijklmnop "
        "https://user:pass@example.test/v1 "
        "ghp_" + "abcdefghijklmnopqrstuvwxyz "
        "AK" + "IAABCDEFGHIJKLMNOP "
        "eyJabcdefgh.eyJijklmnop.abcdefghijk "
        "4111 1111 1111 1111 "
        "-----BEGIN PRIVATE " + "KEY-----\nprivate-material\n"
        "-----END PRIVATE " + "KEY-----"
    )
    redacted = redact_content(source)
    assert "[REDACTED_EMAIL]" in redacted
    assert '"api_key":"[REDACTED]"' in redacted
    assert "Bearer [REDACTED]" in redacted
    assert "https://[REDACTED]@example.test/v1" in redacted
    assert "[REDACTED_KEY]" in redacted
    assert "[REDACTED_JWT]" in redacted
    assert "[REDACTED_NUMBER]" in redacted
    assert "[REDACTED_PRIVATE_KEY]" in redacted
    for secret in (
        "user@example.com",
        "plain-secret",
        "correct horse battery staple",
        "abcdefghijklmnop",
        "private-material",
    ):
        assert secret not in redacted

    unterminated_key = "-----BEGIN RSA PRIVATE " + "KEY-----\n" + ("a" * 10_000)
    assert redact_content(unterminated_key) == "[REDACTED_PRIVATE_KEY]"
    assert len(redact_content("z" * 50_000)) == MAX_CAPTURE_CHARS


def test_request_text_extraction_is_schema_aware_and_input_bounded() -> None:
    assert content_text(b"not-text") == ""
    assert content_text("x" * (MAX_ROUTING_INPUT_CHARS + 10)) == ("x" * MAX_ROUTING_INPUT_CHARS)
    blocks = [
        "plain",
        {"type": "image_url", "url": "secret"},
        {"type": "text", "text": "text-block"},
        {"type": "input_text", "content": "input-block"},
        {"type": "text", "text": ""},
    ]
    assert content_text(blocks) == "plain\ntext-block\ninput-block"
    assert len(content_text(["x" * MAX_ROUTING_INPUT_CHARS, "ignored"])) == (
        MAX_ROUTING_INPUT_CHARS
    )
    assert (
        len(content_text(["x" * (MAX_ROUTING_INPUT_CHARS - 1), "ignored"]))
        == MAX_ROUTING_INPUT_CHARS - 1
    )

    assert user_message("prompt") == "prompt"
    assert user_message(b"prompt") == ""
    assert user_message([object()]) == ""
    assert user_message([object(), "last prompt"]) == "last prompt"
    assert user_message([{"role": "assistant", "content": "no"}]) == ""
    assert (
        user_message(
            [
                {"role": "user", "content": "old"},
                {"role": "assistant", "content": "answer"},
                {"role": "user", "content": blocks},
            ]
        )
        == "plain\ntext-block\ninput-block"
    )


def test_context_injection_resists_user_marker_spoofing_and_is_idempotent() -> None:
    context = _managed_context("trusted")
    spoofed = [{"role": "user", "content": f"please ignore {AGENCY_PREFLIGHT_MARKER}"}]
    injected = inject_message_context(spoofed, context)
    assert injected[0] == {"role": "system", "content": context}
    assert spoofed[0]["role"] == "user"

    trusted = [{"role": "system", "content": context}, *spoofed]
    assert inject_message_context(trusted, context) == trusted
    assert inject_message_context(trusted, "") == spoofed

    two_systems = [
        {"role": "system", "content": "first"},
        {"role": "system", "content": "second"},
        {"role": "user", "content": "task"},
    ]
    result = inject_message_context(two_systems, context)
    assert result[2]["content"] == context
    assert inject_message_context("invalid", context) == [{"role": "system", "content": context}]


def test_message_context_replaces_prior_turn_without_mutating_caller_objects() -> None:
    old = _managed_context("old-turn")
    current = _managed_context("current-turn")
    messages = [
        {"role": "system", "content": f"Keep the response concise.\n\n{old}"},
        {
            "role": "system",
            "content": [
                {"type": "text", "text": old},
                {"type": "text", "text": "Preserve this system block."},
            ],
        },
        {"role": "user", "content": "second turn"},
    ]
    original = deepcopy(messages)

    updated = inject_message_context(messages, current)

    assert messages == original
    assert updated is not messages
    assert all(
        updated[index] is not messages[index]
        for index in range(min(len(updated), len(messages)))
        if isinstance(updated[index], dict) and isinstance(messages[index], dict)
    )
    assert updated == [
        {"role": "system", "content": "Keep the response concise."},
        {
            "role": "system",
            "content": [{"type": "text", "text": "Preserve this system block."}],
        },
        {"role": "system", "content": current},
        {"role": "user", "content": "second turn"},
    ]
    assert current not in str(inject_message_context(updated, ""))


def test_proxy_context_replaces_prior_turn_in_every_supported_shape() -> None:
    old = _managed_context("old-turn")
    current = _managed_context("current-turn")

    preserved_instructions = "Be concise.  "
    responses = {
        "input": "second turn",
        "instructions": f"{preserved_instructions}\n\n{old}",
    }
    responses_original = deepcopy(responses)
    responses_updated = dict(responses)
    inject_proxy_context(responses_updated, responses_updated["input"], current, "responses")
    assert responses == responses_original
    assert responses_updated["instructions"] == f"{preserved_instructions}\n\n{current}"

    completion = {"prompt": f"{old}\n\nsecond turn"}
    completion_original = deepcopy(completion)
    completion_updated = dict(completion)
    inject_proxy_context(completion_updated, completion_updated["prompt"], current, "completion")
    assert completion == completion_original
    assert completion_updated["prompt"] == f"{current}\n\nsecond turn"

    old_with_capsule = (
        f"{old}\n\n"
        "[AGENCY LOADED] Complete current-turn specialist instruction capsule:\n"
        "Earlier Agency specialist capsules are expired and are not applied "
        "unless the specialist is repeated below.\n"
        "- reviewer: Reviews code.\n"
        "  Instructions: Review the implementation."
    )
    full_completion = {"prompt": f"{old_with_capsule}\n\nsecond turn\n\nkeep spacing"}
    full_completion_updated = dict(full_completion)
    inject_proxy_context(
        full_completion_updated,
        full_completion_updated["prompt"],
        current,
        "completion",
    )
    assert full_completion_updated["prompt"] == f"{current}\n\nsecond turn\n\nkeep spacing"

    batch = {"prompt": [f"{old}\n\nfirst", f"{old}\n\nsecond"]}
    batch_original = deepcopy(batch)
    batch_updated = dict(batch)
    inject_proxy_context(batch_updated, batch_updated["prompt"], current, "completion")
    assert batch == batch_original
    assert batch_updated["prompt"] == [
        f"{current}\n\nfirst",
        f"{current}\n\nsecond",
    ]

    anthropic_text = {
        "system": f"Use XML.\n\n{old}",
        "messages": [{"role": "user", "content": "second turn"}],
    }
    anthropic_text_original = deepcopy(anthropic_text)
    anthropic_text_updated = dict(anthropic_text)
    inject_proxy_context(
        anthropic_text_updated,
        anthropic_text_updated["messages"],
        current,
        "anthropic_messages",
    )
    assert anthropic_text == anthropic_text_original
    assert anthropic_text_updated["system"] == f"Use XML.\n\n{current}"

    anthropic_blocks = {
        "system": [
            {"type": "text", "text": "Use XML."},
            {"type": "text", "text": old},
        ],
        "messages": [{"role": "user", "content": "second turn"}],
    }
    anthropic_blocks_original = deepcopy(anthropic_blocks)
    anthropic_blocks_updated = dict(anthropic_blocks)
    inject_proxy_context(
        anthropic_blocks_updated,
        anthropic_blocks_updated["messages"],
        current,
        "anthropic_messages",
    )
    assert anthropic_blocks == anthropic_blocks_original
    assert anthropic_blocks_updated["system"] == [
        {"type": "text", "text": "Use XML."},
        {"type": "text", "text": current},
    ]


def test_literal_preflight_marker_is_preserved_in_every_supported_shape() -> None:
    literal = f"{AGENCY_PREFLIGHT_MARKER} is caller-authored documentation, not context."
    current = _managed_context("current-turn")

    chat = [
        {"role": "system", "content": literal},
        {"role": "user", "content": "task"},
    ]
    chat_original = deepcopy(chat)
    chat_updated = inject_message_context(chat, current)
    assert chat == chat_original
    assert chat_updated == [
        {"role": "system", "content": literal},
        {"role": "system", "content": current},
        {"role": "user", "content": "task"},
    ]

    responses = {"input": "task", "instructions": literal}
    responses_original = deepcopy(responses)
    responses_updated = dict(responses)
    inject_proxy_context(responses_updated, "task", current, "responses")
    assert responses == responses_original
    assert responses_updated["instructions"] == f"{literal}\n\n{current}"

    anthropic_text = {
        "system": literal,
        "messages": [{"role": "user", "content": "task"}],
    }
    anthropic_text_original = deepcopy(anthropic_text)
    anthropic_text_updated = dict(anthropic_text)
    inject_proxy_context(
        anthropic_text_updated,
        anthropic_text_updated["messages"],
        current,
        "anthropic_messages",
    )
    assert anthropic_text == anthropic_text_original
    assert anthropic_text_updated["system"] == f"{literal}\n\n{current}"

    anthropic_blocks = {
        "system": [{"type": "text", "text": literal}],
        "messages": [{"role": "user", "content": "task"}],
    }
    anthropic_blocks_original = deepcopy(anthropic_blocks)
    anthropic_blocks_updated = dict(anthropic_blocks)
    inject_proxy_context(
        anthropic_blocks_updated,
        anthropic_blocks_updated["messages"],
        current,
        "anthropic_messages",
    )
    assert anthropic_blocks == anthropic_blocks_original
    assert anthropic_blocks_updated["system"] == [
        {"type": "text", "text": literal},
        {"type": "text", "text": current},
    ]

    completion = {"prompt": f"{literal}\n\nactual user prompt"}
    completion_original = deepcopy(completion)
    completion_updated = dict(completion)
    inject_proxy_context(
        completion_updated,
        completion_updated["prompt"],
        current,
        "completion",
    )
    assert completion == completion_original
    assert completion_updated["prompt"] == f"{current}\n\n{literal}\n\nactual user prompt"


def test_proxy_context_removes_prior_turn_when_no_current_context() -> None:
    old = _managed_context("old-turn")
    cases = [
        ({"input": "task", "instructions": old}, "task", "responses", "instructions"),
        ({"prompt": f"{old}\n\ntask"}, f"{old}\n\ntask", "completion", "prompt"),
        (
            {
                "system": [{"type": "text", "text": old}],
                "messages": [{"role": "user", "content": "task"}],
            },
            [{"role": "user", "content": "task"}],
            "anthropic_messages",
            "system",
        ),
    ]

    for payload, request_input, call_type, field in cases:
        original = deepcopy(payload)
        updated = dict(payload)
        inject_proxy_context(updated, request_input, "", call_type)
        assert payload == original
        assert old not in str(updated)
        if call_type == "completion":
            assert updated[field] == "task"
        else:
            assert field not in updated


def test_proxy_hook_routes_clean_input_and_removes_stale_context_when_current_is_empty(
    tmp_path: Path,
) -> None:
    old = _managed_context("old-turn")
    current = _managed_context("current-turn")
    callback = AgencyLiteLLMCallback(store=Store(tmp_path / "stale-context.db"))
    routed_inputs: list[Any] = []

    def current_context(**kwargs: Any) -> str:
        routed_inputs.append(kwargs["messages"])
        return current

    callback._routing_context = current_context  # type: ignore[method-assign]
    completion = {
        "model": "task-general",
        "prompt": f"{old}\n\nsecond turn",
    }
    completion_original = deepcopy(completion)
    completion_updated = asyncio.run(
        callback.async_pre_call_hook(None, None, completion, "completion")
    )

    assert completion == completion_original
    assert routed_inputs == ["second turn"]
    assert completion_updated["prompt"] == f"{current}\n\nsecond turn"

    callback._routing_context = lambda **_: ""  # type: ignore[method-assign]
    chat = {
        "model": "task-general",
        "messages": [
            {"role": "system", "content": old},
            {"role": "user", "content": "trivial follow-up"},
        ],
    }
    chat_original = deepcopy(chat)
    chat_updated = asyncio.run(callback.async_pre_call_hook(None, None, chat, "chat_completion"))

    assert chat == chat_original
    assert chat_updated["messages"] == [{"role": "user", "content": "trivial follow-up"}]


def test_proxy_request_shapes_preserve_openai_and_anthropic_contracts() -> None:
    context = _managed_context("routed")
    assert proxy_request_input({"input": "response task"}, "responses") == "response task"
    messages = [{"role": "user", "content": "chat task"}]
    assert proxy_request_input({"messages": messages}, "chat_completion") is messages
    assert proxy_request_input({"prompt": "text task"}, "completion") == "text task"
    assert proxy_request_input({}, "embeddings") is None

    response_payload: dict[str, Any] = {"input": "task"}
    inject_proxy_context(response_payload, "task", context, "responses")
    assert response_payload == {"input": "task", "instructions": context}
    inject_proxy_context(response_payload, "task", context, "responses")
    assert response_payload["instructions"] == context

    with_instructions = {"input": "task", "instructions": "Be concise."}
    inject_proxy_context(with_instructions, "task", context, "responses")
    assert with_instructions["instructions"] == f"Be concise.\n\n{context}"
    invalid_instructions = {"input": "task", "instructions": ["invalid"]}
    inject_proxy_context(invalid_instructions, "task", context, "responses")
    assert invalid_instructions["instructions"] == ["invalid"]

    chat_payload: dict[str, Any] = {"messages": messages}
    inject_proxy_context(chat_payload, messages, context, "chat_completion")
    assert chat_payload["messages"][0]["role"] == "system"

    completion_payload = {"prompt": "Write a poem."}
    inject_proxy_context(completion_payload, "Write a poem.", context, "completion")
    assert completion_payload == {"prompt": f"{context}\n\nWrite a poem."}
    inject_proxy_context(completion_payload, completion_payload["prompt"], context, "completion")
    assert completion_payload == {"prompt": f"{context}\n\nWrite a poem."}
    batch_payload = {"prompt": ["first", [1, 2, 3], context]}
    inject_proxy_context(batch_payload, batch_payload["prompt"], context, "completion")
    assert batch_payload["prompt"] == [
        f"{context}\n\nfirst",
        [1, 2, 3],
        context,
    ]
    token_payload = {"prompt": b"tokenized"}
    inject_proxy_context(token_payload, token_payload["prompt"], context, "completion")
    assert token_payload == {"prompt": b"tokenized"}

    anthropic_none: dict[str, Any] = {"messages": messages}
    inject_proxy_context(anthropic_none, messages, context, "anthropic_messages")
    assert anthropic_none["system"] == context
    anthropic_text = {"system": "Be concise.", "messages": messages}
    inject_proxy_context(anthropic_text, messages, context, "anthropic_messages")
    assert anthropic_text["system"] == f"Be concise.\n\n{context}"
    anthropic_blocks = {
        "system": [{"type": "text", "text": "Be concise."}],
        "messages": messages,
    }
    inject_proxy_context(anthropic_blocks, messages, context, "anthropic_messages")
    assert anthropic_blocks["system"][-1]["text"] == context
    inject_proxy_context(anthropic_blocks, messages, context, "anthropic_messages")
    assert len(anthropic_blocks["system"]) == 2
    invalid_system = {"system": object(), "messages": messages}
    original_system = invalid_system["system"]
    inject_proxy_context(invalid_system, messages, context, "anthropic_messages")
    assert invalid_system["system"] is original_system


def test_adapter_contract_and_skip_prefixes_are_truthful(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = Store(tmp_path / "adapter.db")
    store.record_skill_loaded("session", "skill-one")
    store.record_specialist_loaded("session", "specialist-one")
    store.record_model_receipt(
        trace_id="trace",
        session_id="session",
        resolved_model="gpt-5",
    )
    adapter = LiteLLMAdapter(store=store, config=_config(enabled="true"))
    assert adapter.is_available() is True
    assert store.get_model_receipt("trace")["resolved_model"] == "gpt-5"

    disabled = LiteLLMAdapter(store=store, config=_config(enabled="false"))
    assert disabled.is_available() is False
    monkeypatch.setattr(callback_module, "litellm_health_check", lambda *_: True)
    assert LiteLLMAdapter(store=store, config=_config()).is_available() is True

    receipt = adapter.extract_receipt_from_headers(
        {
            "x-litellm-model-id": "openai/gpt-5",
            "x-litellm-model-api-base": "file://unsafe/path",
        },
        "requested",
    )
    assert receipt["host"] == "litellm"
    assert receipt["api_base"] == ""

    routed: list[str] = []
    prefixes = _config(skip_models=("", "complexity_router", "auto_router/"))
    prefix_adapter = LiteLLMAdapter(store=store, config=prefixes)
    monkeypatch.setattr(
        prefix_adapter,
        "build_preflight_context",
        lambda _session, message, *_args, **_kwargs: (
            routed.append(message) or {"context": "context"}
        ),
    )
    assert prefix_adapter.pre_call_handler("s", "task", "vendor/auto_router/model") is None
    assert prefix_adapter.pre_call_handler("s", "task", "task-general") == {"context": "context"}
    assert routed == ["task"]
    monkeypatch.setattr(
        prefix_adapter,
        "build_preflight_context",
        lambda *_args, **_kwargs: {"context": "fallback"},
    )
    assert prefix_adapter.pre_call_handler("s", "hi", "task-general") == {"context": "fallback"}


def test_store_bound_litellm_uses_its_config_identity_and_explicit_config_wins(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    process_config = tmp_path / "process.yaml"
    process_config.write_text(
        "adapters:\n"
        "  litellm:\n"
        "    enabled: false\n"
        "    skip_models: [process-only]\n"
        "observability:\n"
        "  capture_content: false\n"
        "selector:\n"
        "  trivial_msg_threshold: 100\n",
        encoding="utf-8",
    )
    bound_config = tmp_path / "bound.yaml"
    bound_config.write_text(
        "adapters:\n"
        "  litellm:\n"
        "    enabled: true\n"
        "    skip_models: [bound-skip]\n"
        "observability:\n"
        "  capture_content: true\n"
        "selector:\n"
        "  trivial_msg_threshold: 1\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("AGENCY_CONFIG_PATH", str(process_config))
    store = Store(tmp_path / "agency.db", config_path=bound_config)

    adapter = LiteLLMAdapter(store=store)
    assert adapter.config.config_path == str(bound_config.resolve())
    assert adapter.config.adapters.litellm.enabled == "true"
    assert adapter.is_available() is True
    observed: dict[str, Any] = {}

    def capture_preflight(
        _session: str,
        _message: str,
        _model: str,
        _trace_id: str,
        **kwargs: Any,
    ) -> dict[str, str]:
        observed.update(kwargs)
        return {"context": "bound"}

    monkeypatch.setattr(adapter, "build_preflight_context", capture_preflight)
    assert adapter.pre_call_handler("s", "private@example.com", "bound-skip") is None
    assert adapter.pre_call_handler("s", "private@example.com", "process-only") == {
        "context": "bound"
    }
    assert observed["config"] is adapter.config
    assert observed["config"].selector.trivial_msg_threshold == 1
    assert "[REDACTED_EMAIL]" in observed["persisted_user_message"]

    callback = AgencyLiteLLMCallback(store=store)
    assert callback._config is None
    assert callback.config.adapters.litellm.enabled == "true"
    assert callback.config.config_path == str(bound_config.resolve())
    module = SimpleNamespace(callbacks=[])
    registration = register_litellm_callback(litellm_module=module, store=store)
    assert registration.registered is True
    assert registration.callback is not None
    assert registration.callback.config.config_path == str(bound_config.resolve())

    explicit = _config(enabled="false", capture_content=False)
    assert LiteLLMAdapter(store=store, config=explicit)._config is explicit
    explicit_callback = AgencyLiteLLMCallback(store=store, config=explicit)
    assert explicit_callback.config.adapters.litellm.enabled == "false"
    disabled = register_litellm_callback(
        litellm_module=SimpleNamespace(callbacks=[]),
        store=store,
        config=explicit,
    )
    assert disabled.registered is False


def test_registered_litellm_callback_applies_bound_config_changes_on_next_event(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config_path = tmp_path / "live.yaml"
    config_path.write_text(
        "adapters:\n"
        "  litellm:\n"
        '    enabled: "true"\n'
        "    skip_models: []\n"
        "agents:\n"
        "  disabled: []\n"
        "observability:\n"
        "  capture_content: false\n",
        encoding="utf-8",
    )
    store = Store(tmp_path / "live.db", config_path=config_path)
    module = SimpleNamespace(callbacks=[])
    registration = register_litellm_callback(litellm_module=module, store=store)
    assert registration.registered is True
    callback = registration.callback
    assert callback is not None
    assert callback._config_input is None
    assert callback._config is None
    adapter = callback.adapter
    assert adapter._config_input is None

    observed: list[dict[str, Any]] = []

    def capture_preflight(
        _session: str,
        _message: str,
        _model: str,
        _trace_id: str,
        **kwargs: Any,
    ) -> dict[str, str]:
        observed.append(kwargs)
        return {"context": "live-context"}

    monkeypatch.setattr(adapter, "build_preflight_context", capture_preflight)
    assert (
        callback._routing_context(
            model="allowed-router",
            messages="Review before@example.com",
            payload={"metadata": {"agency_trace_id": "before", "agency_session_id": "session"}},
        )
        == "live-context"
    )
    assert observed[-1]["config"].agents.disabled == ()
    assert observed[-1]["persisted_user_message"] == ""

    state = read_config_state(config_path)
    apply_config_operations(
        [
            {"op": "set", "path": "agents.disabled", "value": ["code-reviewer"]},
            {
                "op": "set",
                "path": "adapters.litellm.skip_models",
                "value": ["blocked-router"],
            },
            {"op": "set", "path": "observability.capture_content", "value": True},
        ],
        expected_revision=state.revision,
        path=config_path,
    )

    assert (
        callback._routing_context(
            model="blocked-router/child",
            messages="Review blocked@example.com",
            payload={"metadata": {"agency_trace_id": "blocked", "agency_session_id": "session"}},
        )
        == ""
    )
    assert len(observed) == 1
    assert (
        callback._routing_context(
            model="allowed-router",
            messages="Review after@example.com",
            payload={"metadata": {"agency_trace_id": "after", "agency_session_id": "session"}},
        )
        == "live-context"
    )
    assert observed[-1]["config"].agents.disabled == ("code-reviewer",)
    assert "[REDACTED_EMAIL]" in observed[-1]["persisted_user_message"]

    state = read_config_state(config_path)
    apply_config_operations(
        [{"op": "set", "path": "adapters.litellm.enabled", "value": "false"}],
        expected_revision=state.revision,
        path=config_path,
    )
    assert (
        callback._routing_context(
            model="allowed-router",
            messages="Review disabled@example.com",
            payload={"metadata": {"agency_trace_id": "disabled", "agency_session_id": "session"}},
        )
        == ""
    )
    assert len(observed) == 2

    state = read_config_state(config_path)
    apply_config_operations(
        [
            {"op": "set", "path": "adapters.litellm.enabled", "value": "true"},
            {"op": "set", "path": "adapters.litellm.skip_models", "value": []},
            {"op": "set", "path": "agents.disabled", "value": []},
            {"op": "set", "path": "observability.capture_content", "value": False},
        ],
        expected_revision=state.revision,
        path=config_path,
    )
    assert (
        callback._routing_context(
            model="allowed-router",
            messages="Review restored@example.com",
            payload={"metadata": {"agency_trace_id": "restored", "agency_session_id": "session"}},
        )
        == "live-context"
    )
    assert len(observed) == 3
    assert observed[-1]["config"].agents.disabled == ()
    assert observed[-1]["persisted_user_message"] == ""


def test_explicit_litellm_config_remains_immutable_after_bound_file_changes(
    tmp_path: Path,
) -> None:
    config_path = tmp_path / "bound.yaml"
    config_path.write_text(
        "adapters:\n  litellm:\n    enabled: false\n"
        "agents:\n  disabled: [code-reviewer]\n"
        "observability:\n  capture_content: true\n",
        encoding="utf-8",
    )
    store = Store(tmp_path / "explicit.db", config_path=config_path)
    explicit = _config(
        enabled="true",
        skip_models=("fixed-router",),
        capture_content=False,
    )
    adapter = LiteLLMAdapter(store=store, config=explicit)
    callback = AgencyLiteLLMCallback(store=store, config=explicit)

    assert adapter.config is explicit
    assert callback.config is explicit
    assert callback.adapter.config is explicit
    assert callback._runtime_active() is True
    assert adapter.config.adapters.litellm.skip_models == ("fixed-router",)
    assert adapter.config.agents.disabled == ()
    assert adapter.config.observability.capture_content is False


@pytest.mark.runtime_configuration_identity
def test_implicit_litellm_fails_closed_on_store_target_drift_while_explicit_survives(
    tmp_path: Path,
) -> None:
    config_path = tmp_path / "litellm.yaml"
    original_db = tmp_path / "original.db"
    replacement_db = tmp_path / "replacement.db"
    config_path.write_text(
        f"adapters:\n  litellm:\n    enabled: true\nstore:\n  db_path: '{original_db}'\n",
        encoding="utf-8",
    )
    store = Store(config_path=config_path)
    implicit = LiteLLMAdapter(store=store)
    callback = AgencyLiteLLMCallback(store=store)
    explicit_config = implicit.config
    explicit = LiteLLMAdapter(store=store, config=explicit_config)
    state = read_config_state(config_path)
    apply_config_operations(
        [{"op": "set", "path": "store.db_path", "value": str(replacement_db)}],
        expected_revision=state.revision,
        path=config_path,
    )

    with pytest.raises(StoreConfigBindingError, match="configured Store path changed"):
        _ = implicit.config
    with pytest.raises(StoreConfigBindingError, match="configured Store path changed"):
        implicit.is_available()
    with pytest.raises(StoreConfigBindingError, match="configured Store path changed"):
        _ = callback.config
    assert explicit.config is explicit_config
    assert explicit.runtime_enabled() is True


def test_callback_fallback_constructor_and_bounded_caches(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    init_calls: list[dict[str, Any]] = []

    def legacy_init(_self: Any, **kwargs: Any) -> None:
        init_calls.append(kwargs)
        if kwargs:
            raise TypeError("legacy signature")

    monkeypatch.setattr(callback_module._CustomLogger, "__init__", legacy_init)
    callback = AgencyLiteLLMCallback(
        store=Store(tmp_path / "legacy.db"),
        config=AgencyConfig(),
    )
    assert init_calls == [{"turn_off_message_logging": True}, {}]

    monkeypatch.setattr(callback_module, "_MAX_DEDUPE_EVENTS", 2)
    assert callback._claim("one") is True
    assert callback._claim("two") is True
    assert callback._claim("one") is False
    assert callback._claim("three") is True
    assert list(callback._recorded_events) == ["one", "three"]

    response: dict[str, Any] = {}
    generated_trace, key = callback._event_key({}, response, None, "success")
    duplicate_trace, duplicate_key = callback._event_key({}, response, None, "failed")
    assert generated_trace.startswith("litellm-terminal:")
    assert duplicate_trace == generated_trace
    assert duplicate_key != key
    assert key.endswith(":success")
    assert duplicate_key.endswith(":failed")
    assert key.startswith(f"terminal:{generated_trace}:")


def test_terminal_callbacks_dedupe_without_response_id_or_start_time(
    tmp_path: Path,
) -> None:
    store = Store(tmp_path / "terminal.db")
    callback = AgencyLiteLLMCallback(store=store, config=AgencyConfig())
    payload = {
        "model": "task-general",
        "metadata": {"agency_trace_id": "stable-trace"},
        "litellm_params": {"custom_llm_provider": "requested-provider"},
        "previous_models": ["one", "two", "three"],
    }
    response = {"model": "anthropic/claude-sonnet"}

    callback.log_success_event(payload, response, None, None)
    asyncio.run(callback.async_log_success_event(payload, response, None, None))

    receipt = store.get_model_receipt("stable-trace")
    assert receipt is not None
    assert receipt["resolved_provider"] == "anthropic"
    assert receipt["resolved_model"] == "claude-sonnet"
    assert receipt["attempted_fallbacks"] == 3
    assert store.runtime_table_counts()["model_receipts"] == 1
    assert store.get_run("stable-trace")["status"] == "evidence_only"

    failed_payload = {
        "model": "task-general",
        "metadata": {"agency_trace_id": "failed-trace"},
        "litellm_params": {"custom_llm_provider": "must-not-promote"},
    }
    failed_response = {"model": "openai/gpt-5"}
    callback.log_failure_event(failed_payload, failed_response, None, None)
    asyncio.run(
        callback.async_log_failure_event(
            failed_payload,
            failed_response,
            None,
            None,
        )
    )
    failed = store.get_model_receipt("failed-trace")
    assert failed is not None
    assert failed["resolved_provider"] == ""
    assert failed["resolved_model"] == "unavailable"
    assert store.get_run("failed-trace")["status"] == "evidence_only"


def test_routing_context_generation_cache_bounds_and_disabled_paths(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class RoutingAdapter:
        host_name = "litellm"

        def __init__(self) -> None:
            self.calls = 0
            self.messages: list[str] = []
            self.trace_ids: list[str] = []

        def pre_call_handler(
            self,
            _session_id: str,
            user_message: str,
            _model: str,
            **kwargs: Any,
        ) -> dict[str, str]:
            self.calls += 1
            self.messages.append(user_message)
            self.trace_ids.append(str(kwargs.get("trace_id") or ""))
            return {"context": "c" * 16_384}

    callback = AgencyLiteLLMCallback(
        store=Store(tmp_path / "routing.db"),
        config=_config(capture_content=True),
    )
    adapter = RoutingAdapter()
    callback._adapter = adapter  # type: ignore[assignment]
    payload: dict[str, Any] = {}
    context = callback._routing_context(
        model="task-general",
        messages="route user@example.com",
        payload=payload,
    )
    assert len(context) == 16_384
    generated_trace = payload["metadata"]["agency_trace_id"]
    assert adapter.trace_ids == [generated_trace]
    assert adapter.messages == ["route user@example.com"]

    assert (
        callback._routing_context(
            model="task-general",
            messages="route user@example.com",
            payload=payload,
        )
        == context
    )
    assert adapter.calls == 1

    oversized_payload = {
        "metadata": {"agency_trace_id": "oversized-trace"},
    }
    original_handler = adapter.pre_call_handler
    adapter.pre_call_handler = lambda *_args, **_kwargs: {"context": "x" * 20_000}  # type: ignore[method-assign]
    with pytest.raises(RuntimeError, match="delivery ceiling"):
        callback._routing_context(
            model="task-general",
            messages="oversized task",
            payload=oversized_payload,
        )
    assert all(key[1] != "oversized-trace" for key in callback._route_contexts)
    adapter.pre_call_handler = original_handler  # type: ignore[method-assign]

    monkeypatch.setattr(callback_module, "_MAX_ROUTE_CONTEXTS", 1)
    second = {
        "metadata": {"agency_trace_id": "second-trace"},
    }
    callback._routing_context(
        model="task-general",
        messages=[{"role": "user", "content": "second task"}],
        payload=second,
    )
    assert [(key[0], key[1]) for key in callback._route_contexts] == [
        ("second-trace", "second-trace")
    ]

    disabled = AgencyLiteLLMCallback(
        store=Store(tmp_path / "disabled.db"),
        config=_config(enabled="false"),
    )
    assert disabled._routing_context(model="m", messages="task", payload={}) == ""
    assert callback._routing_context(model="m", messages=[], payload={}) == ""


def test_route_context_cache_cannot_bypass_store_request_correlation(tmp_path: Path) -> None:
    callback = AgencyLiteLLMCallback(
        store=Store(tmp_path / "route-correlation.db"),
        config=AgencyConfig(),
    )
    original = {
        "metadata": {
            "agency_session_id": "session-a",
            "agency_trace_id": "shared-trace",
        }
    }
    context = callback._routing_context(
        model="task-general",
        messages="Review this implementation.",
        payload=original,
    )
    assert context

    with pytest.raises(ValueError, match="different preflight request"):
        callback._routing_context(
            model="task-general",
            messages="Review this implementation.",
            payload={
                "metadata": {
                    "agency_session_id": "session-b",
                    "agency_trace_id": "shared-trace",
                }
            },
        )
    with pytest.raises(ValueError, match="different preflight request"):
        callback._routing_context(
            model="task-general",
            messages="Implement a different request.",
            payload=original,
        )


def test_route_context_cache_reenters_adapter_when_model_changes(tmp_path: Path) -> None:
    class RoutingAdapter:
        host_name = "litellm"

        def __init__(self) -> None:
            self.models: list[str] = []

        def pre_call_handler(self, _session: str, _message: str, model: str, **_kwargs: Any):
            self.models.append(model)
            return {"context": f"context:{model}"}

    callback = AgencyLiteLLMCallback(
        store=Store(tmp_path / "route-model.db"),
        config=AgencyConfig(),
    )
    adapter = RoutingAdapter()
    callback._adapter = adapter  # type: ignore[assignment]
    payload = {
        "metadata": {
            "agency_session_id": "session",
            "agency_trace_id": "trace",
        }
    }

    assert callback._routing_context(model="model-a", messages="task", payload=payload) == (
        "context:model-a"
    )
    assert callback._routing_context(model="model-b", messages="task", payload=payload) == (
        "context:model-b"
    )
    assert adapter.models == ["model-a", "model-b"]


def test_route_context_cleanup_is_exact_to_session_and_trace(tmp_path: Path) -> None:
    callback = AgencyLiteLLMCallback(
        store=Store(tmp_path / "route-cleanup.db"),
        config=AgencyConfig(),
    )
    callback._route_contexts[("session", "trace", "request-a")] = "a"
    callback._route_contexts[("session", "trace", "request-b")] = "b"
    callback._route_contexts[("other", "trace", "request-c")] = "c"

    callback._discard_route_contexts("session", "trace")

    assert callback._route_contexts == {("other", "trace", "request-c"): "c"}


def test_receipt_failure_before_event_identity_never_unclaims_empty_key(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    callback = AgencyLiteLLMCallback(
        store=Store(tmp_path / "event-key-failure.db"),
        config=AgencyConfig(),
    )
    unclaimed: list[str] = []

    def fail_event_key(*_args: Any, **_kwargs: Any) -> tuple[str, str]:
        raise RuntimeError("unavailable")

    monkeypatch.setattr(callback, "_event_key", fail_event_key)
    monkeypatch.setattr(callback, "_unclaim", unclaimed.append)
    callback.log_success_event({}, {}, None, None)

    assert unclaimed == []
    assert "LiteLLM evidence callback failed: RuntimeError" in caplog.text


def test_async_hooks_are_nonblocking_schema_correct_and_failure_isolated(
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    callback = AgencyLiteLLMCallback(
        store=Store(tmp_path / "hooks.db"),
        config=AgencyConfig(),
    )
    caller_thread = threading.get_ident()
    worker_threads: list[int] = []

    def context(**_: Any) -> str:
        worker_threads.append(threading.get_ident())
        return f"{AGENCY_PREFLIGHT_MARKER} routed"

    callback._routing_context = context  # type: ignore[method-assign]
    responses_request = {
        "model": "task-general",
        "input": "Review this implementation",
        "instructions": "Be concise.",
    }
    updated = asyncio.run(callback.async_pre_call_hook(None, None, responses_request, "responses"))
    assert worker_threads[0] != caller_thread
    assert updated["input"] == responses_request["input"]
    assert updated["instructions"].startswith("Be concise.\n\n[AGENCY PREFLIGHT]")
    assert "messages" not in updated

    prompt_request = {"model": "task-general", "prompt": "Review this"}
    prompt_updated = asyncio.run(
        callback.async_pre_call_hook(None, None, prompt_request, "completion")
    )
    assert prompt_updated["prompt"].startswith("[AGENCY PREFLIGHT] routed\n\n")
    assert "messages" not in prompt_updated

    unsupported = {"model": "embedding", "input": "text"}
    assert (
        asyncio.run(callback.async_pre_call_hook(None, None, unsupported, "embedding"))
        is unsupported
    )

    sdk = asyncio.run(
        callback.async_pre_request_hook(
            "task-general",
            [{"role": "user", "content": "task"}],
            {"temperature": 0},
        )
    )
    assert sdk["messages"][0]["role"] == "system"

    callback._routing_context = lambda **_: ""  # type: ignore[method-assign]
    sdk_without_context = asyncio.run(
        callback.async_pre_request_hook(
            "task-general",
            [{"role": "user", "content": "task"}],
            {"temperature": 0},
        )
    )
    assert sdk_without_context == {"temperature": 0}
    proxy_without_context = asyncio.run(
        callback.async_pre_call_hook(
            None,
            None,
            {"model": "task-general", "messages": []},
            "chat_completion",
        )
    )
    assert proxy_without_context == {"model": "task-general", "messages": []}

    pre_threads: list[int] = []
    callback.log_pre_api_call = (  # type: ignore[method-assign]
        lambda *_args, **_kwargs: pre_threads.append(threading.get_ident())
    )
    asyncio.run(callback.async_log_pre_api_call("m", [], {}))
    assert pre_threads[0] != caller_thread

    def broken(**_: Any) -> str:
        raise sqlite3.OperationalError("secret database detail")

    callback._routing_context = broken  # type: ignore[method-assign]
    kwargs = {"sentinel": True}
    assert asyncio.run(callback.async_pre_request_hook("m", [], kwargs)) is kwargs
    proxy_data = {"model": "m", "messages": []}
    assert (
        asyncio.run(callback.async_pre_call_hook(None, None, proxy_data, "chat_completion"))
        is proxy_data
    )
    assert "OperationalError" in caplog.text
    assert "secret database detail" not in caplog.text


def test_sync_pre_hook_failure_isolated_and_registration_edge_cases(
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    callback = AgencyLiteLLMCallback(
        store=Store(tmp_path / "registration.db"),
        config=AgencyConfig(),
    )

    def broken(**_: Any) -> str:
        raise RuntimeError("sensitive prompt")

    callback._routing_context = broken  # type: ignore[method-assign]
    callback.log_pre_api_call("model", [], {})
    assert "RuntimeError" in caplog.text
    assert "sensitive prompt" not in caplog.text

    disabled = register_litellm_callback(
        litellm_module=SimpleNamespace(callbacks=[]),
        config=_config(enabled="false"),
    )
    assert disabled.registered is False
    assert disabled.reason == "disabled by Agency Runtime config"

    empty_module = SimpleNamespace(callbacks=None)
    empty_result = register_litellm_callback(
        litellm_module=empty_module,
        config=AgencyConfig(),
    )
    assert empty_result.registered is True
    assert len(empty_module.callbacks) == 1

    existing = object()
    scalar_module = SimpleNamespace(callbacks=existing)
    scalar_result = register_litellm_callback(
        litellm_module=scalar_module,
        config=AgencyConfig(),
    )
    assert scalar_result.registered is True
    assert scalar_module.callbacks[0] is existing

    class RejectingModule:
        @property
        def callbacks(self) -> tuple[Any, ...]:
            return ()

        @callbacks.setter
        def callbacks(self, _value: Any) -> None:
            raise RuntimeError("must not leak")

    rejected = register_litellm_callback(
        litellm_module=RejectingModule(),
        config=AgencyConfig(),
    )
    assert rejected.available is True
    assert rejected.registered is False
    assert rejected.reason == "callback registry rejected assignment: RuntimeError"
    assert "must not leak" not in rejected.reason
