"""Focused contracts for the optional LiteLLM callback bridge."""

from __future__ import annotations

import asyncio
import sqlite3
import threading
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import datetime, timezone
from multiprocessing import get_context
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from agency_runtime.adapters.litellm.callback import (
    AgencyLiteLLMCallback,
    LiteLLMRegistration,
    litellm_proxy_callback_config,
    register_litellm_callback,
)
from agency_runtime.core.config import AgencyConfig, ObservabilityConfig
from agency_runtime.core.selector.cache import clear_cache
from agency_runtime.core.store.sqlite import Store

START = datetime(2026, 7, 10, 12, 0, tzinfo=timezone.utc)
END = datetime(2026, 7, 10, 12, 0, 1, tzinfo=timezone.utc)


def _payload(trace_id: str) -> dict[str, Any]:
    return {
        "model": "task-general",
        "messages": [{"role": "user", "content": "secret prompt"}],
        "api_key": "sk-never-persist-this",
        "litellm_params": {
            "custom_llm_provider": "openai",
            "metadata": {
                "agency_trace_id": trace_id,
                "agency_session_id": "session-1",
            },
        },
    }


def _success_response(response_id: str = "response-1") -> dict[str, Any]:
    return {
        "id": response_id,
        "model": "openai/gpt-5.4-mini",
        "_hidden_params": {
            "additional_headers": {
                "x-litellm-model-group": "task-general",
                "x-litellm-model-api-base": "https://user:secret@api.openai.com/v1?key=hidden",
                "x-litellm-model-id": "deployment-42",
                "x-litellm-attempted-fallbacks": "2",
                "authorization": "Bearer never-copy-this",
            }
        },
    }


def _process_write_receipt(db_path: str, index: int) -> None:
    """Spawn-safe worker used by both Windows and POSIX test runners."""
    store = Store(Path(db_path))
    callback = AgencyLiteLLMCallback(store=store, config=AgencyConfig())
    callback.log_success_event(
        _payload(f"process-trace-{index}"),
        _success_response(f"process-response-{index}"),
        START,
        END,
    )


def _db_text(store: Store, sql: str, params: tuple[Any, ...] = ()) -> str:
    conn = sqlite3.connect(store.db_path)
    try:
        row = conn.execute(sql, params).fetchone()
        return "" if row is None or row[0] is None else str(row[0])
    finally:
        conn.close()


def test_programmatic_registration_is_thread_safe_idempotent_and_preserves_callbacks(
    tmp_path: Path,
) -> None:
    existing = object()
    fake_litellm = SimpleNamespace(callbacks=[existing])
    store = Store(tmp_path / "agency.db")

    def register(_: int) -> LiteLLMRegistration:
        return register_litellm_callback(
            litellm_module=fake_litellm,
            store=store,
            config=AgencyConfig(),
        )

    with ThreadPoolExecutor(max_workers=12) as executor:
        results = list(executor.map(register, range(48)))

    agency_callbacks = [
        callback
        for callback in fake_litellm.callbacks
        if getattr(callback, "_agency_runtime_callback", False)
    ]
    assert fake_litellm.callbacks[0] is existing
    assert len(agency_callbacks) == 1
    assert all(result.available and result.registered for result in results)
    assert sum(not result.already_registered for result in results) == 1


def test_registration_is_safe_noop_when_litellm_is_absent(monkeypatch: pytest.MonkeyPatch) -> None:
    import agency_runtime.adapters.litellm.callback as module

    def missing(_: str) -> Any:
        raise ImportError("not installed")

    monkeypatch.setattr(module.importlib, "import_module", missing)
    result = register_litellm_callback(config=AgencyConfig())
    assert result == LiteLLMRegistration(
        available=False,
        registered=False,
        reason="LiteLLM is not installed",
    )


def test_proxy_config_uses_dotted_callback_and_metadata_only_default() -> None:
    fragment = litellm_proxy_callback_config(AgencyConfig())
    assert fragment == {
        "litellm_settings": {
            "callbacks": "agency_runtime.adapters.litellm.callback.proxy_handler_instance",
            "turn_off_message_logging": True,
        }
    }


def test_proxy_config_never_enables_litellm_raw_logging_and_respects_disabled_adapter(
    tmp_path: Path,
) -> None:
    base = AgencyConfig()
    capture = replace(
        base,
        observability=ObservabilityConfig(capture_content=True, retention_days=30),
    )
    disabled = replace(
        base,
        adapters=replace(
            base.adapters,
            litellm=replace(base.adapters.litellm, enabled="false"),
        ),
    )

    assert (
        litellm_proxy_callback_config(capture)["litellm_settings"]["turn_off_message_logging"]
        is True
    )
    assert litellm_proxy_callback_config(disabled) == {
        "litellm_settings": {"turn_off_message_logging": True}
    }

    store = Store(tmp_path / "disabled.db")
    callback = AgencyLiteLLMCallback(store=store, config=disabled)
    callback.log_success_event(_payload("disabled-trace"), _success_response(), START, END)
    assert store.runtime_table_counts()["model_receipts"] == 0


def test_success_callback_records_authoritative_sanitized_metadata_only_receipt(
    tmp_path: Path,
) -> None:
    store = Store(tmp_path / "agency.db")
    callback = AgencyLiteLLMCallback(store=store, config=AgencyConfig())

    callback.log_success_event(_payload("trace-success"), _success_response(), START, END)

    receipt = store.get_model_receipt("trace-success")
    assert receipt is not None
    assert receipt["session_id"] == "session-1"
    assert receipt["requested_model"] == "task-general"
    assert receipt["model_group"] == "task-general"
    assert receipt["resolved_provider"] == "openai"
    assert receipt["resolved_model"] == "gpt-5.4-mini"
    assert receipt["api_base"] == "https://api.openai.com/v1"
    assert receipt["attempted_fallbacks"] == 2
    assert receipt["model_id"] == "deployment-42"
    assert receipt["source"] == "litellm"
    assert receipt["status"] == "success"
    database_text = (tmp_path / "agency.db").read_bytes()
    assert b"secret prompt" not in database_text
    assert b"sk-never-persist-this" not in database_text
    assert b"never-copy-this" not in database_text
    assert b"user:secret" not in database_text


def test_failure_callback_never_promotes_requested_or_selected_model_to_actual(
    tmp_path: Path,
) -> None:
    store = Store(tmp_path / "agency.db")
    callback = AgencyLiteLLMCallback(store=store, config=AgencyConfig())
    payload = _payload("trace-failed")
    payload["exception"] = RuntimeError("Bearer highly-sensitive-error-detail")

    callback.log_failure_event(payload, _success_response(), START, END)

    receipt = store.get_model_receipt("trace-failed")
    assert receipt is not None
    assert receipt["status"] == "failed"
    assert receipt["resolved_model"] == "unavailable"
    assert b"highly-sensitive-error-detail" not in (tmp_path / "agency.db").read_bytes()


def test_sync_and_async_callbacks_dedupe_same_litellm_event(tmp_path: Path) -> None:
    store = Store(tmp_path / "agency.db")
    callback = AgencyLiteLLMCallback(store=store, config=AgencyConfig())
    payload = _payload("trace-dedupe")
    response = _success_response()

    callback.log_success_event(payload, response, START, END)
    asyncio.run(callback.async_log_success_event(payload, response, START, END))

    counts = store.runtime_table_counts()
    assert counts["model_receipts"] == 1


@pytest.mark.skip(reason="ADR-0087: needs full inference nomination-delivery flow")
def test_proxy_hook_injects_context_and_correlates_routing_with_receipt_trace(
    tmp_path: Path,
) -> None:
    clear_cache()
    store = Store(tmp_path / "agency.db")
    store._activate_prevalidated_agent(
        {
            "slug": "security-reviewer",
            "name": "Security Reviewer",
            "description": "Reviews Python APIs for SQL injection vulnerabilities and security tests",
            "prompt_body": (
                "Review Python APIs for SQL injection vulnerabilities and "
                "produce evidence-backed security test recommendations."
            ),
            "division": "engineering",
            "categories": ["security", "testing"],
            "capabilities": ["python", "security review", "test automation"],
            "authority": "review",
            "context_mode": "direct_safe",
            "required_tools": [],
            "supported_hosts": ["codex", "claude", "hermes", "openclaw"],
            "supported_platforms": ["windows", "linux"],
            "audit_status": "approved",
            "audit_revision": "litellm-v1",
            "routing_contract_valid": True,
            "outcomes": ["Review Python APIs for SQL injection vulnerabilities"],
            "artifact_kinds": ["review-report"],
            "lifecycle_phases": ["review"],
            "domains": ["security"],
            "version": "1.0.0",
        }
    )
    base_config = AgencyConfig()
    callback = AgencyLiteLLMCallback(
        store=store,
        config=replace(
            base_config,
            ollama=replace(base_config.ollama, enabled=False),
        ),
    )
    request = {
        "model": "task-general",
        "metadata": {
            "agency_trace_id": "route-trace",
            "agency_session_id": "route-session",
        },
        "messages": [
            {
                "role": "user",
                "content": "Review the Python API for SQL injection vulnerabilities and write security tests.",
            }
        ],
    }

    updated = asyncio.run(callback.async_pre_call_hook(None, None, request, "completion"))

    assert updated is not request
    assert updated["messages"][0]["role"] == "system"
    assert "[AGENCY PREFLIGHT]" in updated["messages"][0]["content"]
    activity = store.recent_runtime_activity(limit=10)
    assert len(activity["routing"]) == 1
    assert activity["routing"][0]["trace_id"] == "route-trace"
    assert activity["routing"][0]["session_id"] == "route-session"
    assert "security-reviewer" in activity["routing"][0]["selected_ids"]
    assert (
        _db_text(store, "SELECT user_message FROM runs WHERE trace_id = ?", ("route-trace",)) == ""
    )


def test_concurrent_pre_hooks_persist_one_routing_decision_per_trace(tmp_path: Path) -> None:
    clear_cache()
    store = Store(tmp_path / "agency.db")
    store._activate_prevalidated_agent(
        {
            "slug": "python-reviewer",
            "name": "Python Reviewer",
            "description": "Reviews Python API code and writes tests",
            "prompt_body": (
                "Review Python API code and produce focused regression-test recommendations."
            ),
        }
    )
    callback = AgencyLiteLLMCallback(store=store, config=AgencyConfig())
    messages = [{"role": "user", "content": "Review this Python API and write regression tests."}]

    def invoke(_: int) -> None:
        callback.log_pre_api_call(
            "task-general",
            messages,
            {"metadata": {"agency_trace_id": "shared-route-trace"}},
        )

    with ThreadPoolExecutor(max_workers=12) as executor:
        list(executor.map(invoke, range(36)))

    activity = store.recent_runtime_activity(limit=50)
    matching = [row for row in activity["routing"] if row["trace_id"] == "shared-route-trace"]
    assert len(matching) == 1


def test_async_proxy_hook_offloads_blocking_routing_from_event_loop(tmp_path: Path) -> None:
    callback = AgencyLiteLLMCallback(store=Store(tmp_path / "agency.db"), config=AgencyConfig())
    caller_thread = threading.get_ident()
    routed_threads: list[int] = []

    def fake_routing_context(**_: Any) -> str:
        routed_threads.append(threading.get_ident())
        return "[AGENCY PREFLIGHT] test context"

    callback._routing_context = fake_routing_context  # type: ignore[method-assign]
    request = {
        "model": "task-general",
        "messages": [{"role": "user", "content": "Review this implementation."}],
    }
    updated = asyncio.run(callback.async_pre_call_hook(None, None, request, "completion"))

    assert routed_threads and routed_threads[0] != caller_thread
    assert "[AGENCY PREFLIGHT]" in updated["messages"][0]["content"]


@pytest.mark.parametrize(
    ("existing_system", "expected_type"),
    [
        ("Keep the response concise.", str),
        ([{"type": "text", "text": "Keep the response concise."}], list),
    ],
)
def test_anthropic_proxy_hook_uses_top_level_system_field(
    tmp_path: Path,
    existing_system: Any,
    expected_type: type,
) -> None:
    callback = AgencyLiteLLMCallback(store=Store(tmp_path / "agency.db"), config=AgencyConfig())
    callback._routing_context = lambda **_: "[AGENCY PREFLIGHT] routed"  # type: ignore[method-assign]
    request = {
        "model": "claude-sonnet",
        "system": existing_system,
        "messages": [{"role": "user", "content": "Review this implementation."}],
    }

    updated = asyncio.run(callback.async_pre_call_hook(None, None, request, "anthropic_messages"))

    assert isinstance(updated["system"], expected_type)
    assert "[AGENCY PREFLIGHT]" in str(updated["system"])
    assert all(message["role"] != "system" for message in updated["messages"])


def test_opt_in_content_capture_is_redacted_before_store(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cfg = replace(
        AgencyConfig(),
        observability=ObservabilityConfig(capture_content=True, retention_days=30),
    )
    monkeypatch.setattr("agency_runtime.core.config.load_config", lambda *args, **kwargs: cfg)
    store = Store(tmp_path / "agency.db")
    store._activate_prevalidated_agent(
        {
            "slug": "security-reviewer",
            "name": "Security Reviewer",
            "description": "Reviews security vulnerabilities",
            "prompt_body": (
                "Review security vulnerabilities and return bounded, evidence-backed findings."
            ),
        }
    )
    callback = AgencyLiteLLMCallback(store=store, config=cfg)
    request = {
        "model": "task-general",
        "metadata": {"agency_trace_id": "capture-trace"},
        "messages": [
            {
                "role": "user",
                "content": (
                    "Review access for person@example.com with "
                    "Authorization Bearer abcdefghijklmnop and api_key=sk-abcdef1234567890"
                ),
            }
        ],
    }

    asyncio.run(callback.async_pre_call_hook(None, None, request, "completion"))

    captured = _db_text(
        store, "SELECT user_message FROM runs WHERE trace_id = ?", ("capture-trace",)
    )
    assert "[REDACTED_EMAIL]" in captured
    assert "Bearer [REDACTED]" in captured
    assert "api_key=[REDACTED]" in captured
    assert "person@example.com" not in captured
    assert "abcdefghijklmnop" not in captured
    assert "sk-abcdef1234567890" not in captured


def test_spawned_workers_write_receipts_safely_to_one_store(tmp_path: Path) -> None:
    """The spawn start method matches Windows and is available on Linux."""
    db_path = tmp_path / "multiprocess.db"
    Store(db_path)  # migrate once before workers start
    context = get_context("spawn")
    processes = [
        context.Process(target=_process_write_receipt, args=(str(db_path), index))
        for index in range(4)
    ]
    for process in processes:
        process.start()
    for process in processes:
        process.join(timeout=20)
        assert process.exitcode == 0

    store = Store(db_path)
    assert store.runtime_table_counts()["model_receipts"] == 4
    for index in range(4):
        receipt = store.get_model_receipt(f"process-trace-{index}")
        assert receipt is not None
        assert receipt["status"] == "success"


def test_callback_failures_are_isolated_from_model_traffic(
    caplog: pytest.LogCaptureFixture,
) -> None:
    class BrokenStore:
        def record_model_receipt(self, **kwargs: Any) -> None:
            raise sqlite3.OperationalError("database is unavailable")

    callback = AgencyLiteLLMCallback(store=BrokenStore(), config=AgencyConfig())  # type: ignore[arg-type]
    callback.log_success_event(_payload("trace-broken"), _success_response(), START, END)
    assert "OperationalError" in caplog.text


@pytest.mark.parametrize("separator", ["/", "\\"])
def test_callback_activation_contract_is_path_separator_independent(separator: str) -> None:
    """No generated callback path depends on Windows/POSIX filesystem syntax."""
    del separator
    config = litellm_proxy_callback_config(AgencyConfig())
    callback_path = config["litellm_settings"]["callbacks"]
    assert "/" not in callback_path
    assert "\\" not in callback_path
