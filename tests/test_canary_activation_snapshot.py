from __future__ import annotations

import json
import os
from hashlib import sha256
from pathlib import Path

import pytest

from agency_runtime.core.config import reset_config_cache
from agency_runtime.core.host_capabilities import native_adapter_capability_receipt
from agency_runtime.core.preflight import run_preflight
from agency_runtime.core.store.sqlite import Store
from tests.runtime_support import write_provider_config

_REQUEST = "Review this Python code for correctness"


@pytest.fixture()
def store(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    config_path = tmp_path / "agency.yaml"
    write_provider_config(config_path)
    monkeypatch.setenv("AGENCY_CONFIG_PATH", str(config_path))
    reset_config_cache()
    try:
        yield Store(tmp_path / "agency.db", config_path=config_path)
    finally:
        reset_config_cache()


def _keys(value: object) -> set[str]:
    if isinstance(value, dict):
        return {str(key) for key in value} | {
            nested for item in value.values() for nested in _keys(item)
        }
    if isinstance(value, list):
        return {nested for item in value for nested in _keys(item)}
    return set()


def test_canary_activation_snapshot_projects_exact_preflight_failure(
    store: Store,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from agency_runtime.core.selector import pipeline

    request = "Diagnose the exact preflight failure without retaining this request."
    monkeypatch.setattr(
        pipeline,
        "route",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            TimeoutError("private provider timeout detail")
        ),
    )
    with pytest.raises(TimeoutError, match="private provider timeout detail"):
        run_preflight(
            store,
            session_id="failed-session",
            trace_id="failed-trace",
            user_message=request,
            host="codex",
            capability_receipt=native_adapter_capability_receipt(
                "codex",
                platform="windows" if os.name == "nt" else "linux",
                session_id="failed-session",
                trace_id="failed-trace",
            ),
        )

    query_hash = sha256(request.encode("utf-8")).hexdigest()
    snapshot = store.get_canary_activation_snapshot(host="codex", query_hash=query_hash)

    assert snapshot["proven"] is False
    assert snapshot["reason"] == "preflight_failed"
    assert snapshot["session_id"] == "failed-session"
    assert snapshot["trace_id"] == "failed-trace"
    assert snapshot["cardinalities"]["routes"] == 0
    assert snapshot["cardinalities"]["runs"] == 1
    assert snapshot["cardinalities"]["preflight_failures"] == 1
    assert snapshot["run"]["status"] == "preflight_failed"
    assert snapshot["preflight_failure"]["stage"] == "routing"
    assert snapshot["preflight_failure"]["reason_code"] == "routing_failed"
    assert snapshot["preflight_failure"]["exception_category"] == "timeout"
    encoded = json.dumps(snapshot, sort_keys=True)
    assert request not in encoded
    assert "private provider timeout detail" not in encoded
