"""AR-440 / ADR-0253: a stale hook runtime names itself when a turn cannot be verified.

A host session keeps calling the launcher of the digest it loaded at start.
After a reinstall adds a configuration key that runtime does not know, every
hook in the old session fails while opening the store; the Stop boundary
used to fail closed with the generic verification message and the prompt
hook recorded nothing, with only an exception class on stderr. These tests
pin that a boundary failure beside a runtime drift names both projections,
the failure class and the restart, that the shapes and the fail-open prompt
path are unchanged, and that a failure without drift keeps its reason.
"""

from __future__ import annotations

import io
import json
import logging
import sys
import types
from typing import Any

import pytest

from agency_runtime.adapters import hooks
from agency_runtime.core.configuration_contracts import ConfigValidationError
from agency_runtime.core.runtime_staleness import RuntimeStaleness

_RUNNING = "37c1bf7d5eb0625b32c0966845c5f4038b768febf535f7d9256b6339d6394ede"
_INSTALLED = "9cb87800ea8a2f4c0b7d6e5a1c3b9f8e7d6c5b4a3928170f6e5d4c3b2a190807"
_DRIFT = RuntimeStaleness(running_digest=_RUNNING, installed_digest=_INSTALLED, host="claude")
_GENERIC = (
    "Agency Runtime could not verify or persist the turn-scoped evidence contract. "
    "Do not publish this response; restore the evidence store and start a new turn."
)


def _run(
    monkeypatch: pytest.MonkeyPatch,
    *,
    host: str,
    event: str,
    drift: RuntimeStaleness | None,
    failure: BaseException | None = None,
) -> tuple[dict[str, Any], str]:
    """Drive one hook event whose store open fails, with or without drift."""

    def store_factory(*args: Any, **kwargs: Any) -> Any:
        raise failure or ConfigValidationError("dashboard: contains unsupported fields")

    monkeypatch.setattr(hooks, "Store", store_factory)
    monkeypatch.setattr(
        "agency_runtime.core.runtime_staleness.runtime_staleness",
        lambda *, host="": drift,
    )
    monkeypatch.setattr(
        "agency_runtime.core.runtime_control.read_bound_enforcement_runtime_control",
        lambda path: ({"enabled": True}, "test"),
    )
    output = io.BytesIO()
    errors = io.StringIO()
    payload = json.dumps({"hook_event_name": event, "session_id": "session-stale"}).encode()
    assert (
        hooks._run_hook_stdio(
            host,
            config_path="/nonexistent/agency.yaml",
            runtime_control_path="/nonexistent/control.json",
            expected_event=event,
            input_stream=io.BytesIO(payload),
            output_stream=output,
            error_stream=errors,
        )
        == 0
    )
    return json.loads(output.getvalue().decode() or "{}"), errors.getvalue()


def test_a_stale_stop_names_both_projections_the_failure_and_the_restart(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    result, stderr = _run(monkeypatch, host="claude", event="Stop", drift=_DRIFT)

    assert result["continue"] is False
    reason = result["stopReason"]
    assert reason.startswith(
        "Agency Runtime could not verify or persist the turn-scoped evidence contract."
    )
    assert f"run projection {_RUNNING[:12]}" in reason
    assert f"the host installed {_INSTALLED[:12]}" in reason
    assert "ConfigValidationError" in reason
    assert "Restart the claude session" in reason
    # Content-free: the exception message never reaches the host.
    assert "unsupported fields" not in reason
    assert "ConfigValidationError; response publication blocked" in stderr
    assert f"stale_runtime running={_RUNNING[:12]} installed={_INSTALLED[:12]}" in stderr


def test_a_stale_stop_on_zcode_keeps_the_block_shape(monkeypatch: pytest.MonkeyPatch) -> None:
    result, _ = _run(monkeypatch, host="zcode", event="Stop", drift=_DRIFT)

    assert result["decision"] == "block"
    assert f"{_RUNNING[:12]}" in result["reason"]
    assert "Restart the zcode session" in result["reason"]


def test_a_stop_failure_without_drift_keeps_the_generic_reason(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    result, stderr = _run(monkeypatch, host="claude", event="Stop", drift=None)

    assert result == {"continue": False, "stopReason": _GENERIC}
    assert "stale_runtime" not in stderr


def test_a_stale_prompt_hook_still_publishes_and_names_the_drift(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    with caplog.at_level(logging.ERROR, logger="agency_runtime.adapters.hooks"):
        result, stderr = _run(monkeypatch, host="claude", event="UserPromptSubmit", drift=_DRIFT)

    assert result == {}
    assert "host operation continues" in stderr
    assert f"stale_runtime running={_RUNNING[:12]}" in stderr
    records = [
        r for r in caplog.records if r.getMessage() == "preflight_unavailable_publishing_anyway"
    ]
    assert records
    assert getattr(records[-1], "stale_runtime", "") == (
        f"stale_runtime running={_RUNNING[:12]} installed={_INSTALLED[:12]}"
    )
    assert "unsupported fields" in getattr(records[-1], "cause", "")


def test_a_drift_read_that_raises_is_treated_as_no_drift(monkeypatch: pytest.MonkeyPatch) -> None:
    def explode(*, host: str = "") -> RuntimeStaleness | None:
        raise RuntimeError("pointer unreadable")

    monkeypatch.setattr("agency_runtime.core.runtime_staleness.runtime_staleness", explode)
    assert hooks._stale_runtime_drift("claude") is None


def test_a_drift_import_that_fails_is_treated_as_no_drift_and_still_blocks(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # A partially staged projection can lack the staleness module; the Stop
    # boundary must still fail closed with the generic reason, never escape.
    monkeypatch.setitem(
        sys.modules, "agency_runtime.core.runtime_staleness", types.ModuleType("stub")
    )
    assert hooks._stale_runtime_drift("claude") is None

    def store_factory(*args: Any, **kwargs: Any) -> Any:
        raise ConfigValidationError("dashboard: contains unsupported fields")

    monkeypatch.setattr(hooks, "Store", store_factory)
    monkeypatch.setattr(
        "agency_runtime.core.runtime_control.read_bound_enforcement_runtime_control",
        lambda path: ({"enabled": True}, "test"),
    )
    output = io.BytesIO()
    payload = json.dumps({"hook_event_name": "Stop", "session_id": "session-stale"}).encode()
    assert (
        hooks._run_hook_stdio(
            "claude",
            config_path="/nonexistent/agency.yaml",
            runtime_control_path="/nonexistent/control.json",
            expected_event="Stop",
            input_stream=io.BytesIO(payload),
            output_stream=output,
            error_stream=io.StringIO(),
        )
        == 0
    )
    assert json.loads(output.getvalue().decode()) == {"continue": False, "stopReason": _GENERIC}


def test_the_reason_is_bounded_and_sanitises_the_failure_class() -> None:
    reason = hooks._stale_runtime_reason("claude", "Weird<Class>Name", _DRIFT)
    assert "WeirdClassName" in reason
    assert "<" not in reason
    assert len(reason.encode("ascii")) < 1024
