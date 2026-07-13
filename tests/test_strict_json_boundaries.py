"""Strict-JSON regressions for external and persisted-local boundaries."""

from __future__ import annotations

import json
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

from agency_runtime.adapters.base import _tool_failure_reason
from agency_runtime.cli.config_wizard import (
    WizardDependencies,
    _fetch_models_custom,
)
from agency_runtime.core import canary, detect, doctor, smoke
from agency_runtime.core.cli_transport import _parse_claude, _parse_codex
from agency_runtime.core.delegation.backend_command import CommandBackend
from agency_runtime.core.installer_contracts import NativeCommandResult
from agency_runtime.core.installer_native import _json_output
from agency_runtime.core.selector import judge
from agency_runtime.core.store.queries import (
    normalize_activity_rows,
    normalize_snapshot,
)
from agency_runtime.core.store.roster import _decode_json_list

_DUPLICATE_OBJECT = b'{"value":1,"value":2}'
_NON_FINITE_OBJECT = b'{"value":NaN}'


class _Response:
    def __init__(self, payload: bytes) -> None:
        self.payload = payload
        self.status = 200

    def __enter__(self) -> _Response:
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def read(self, amount: int = -1) -> bytes:
        return self.payload if amount < 0 else self.payload[:amount]


@pytest.mark.parametrize("module", [detect, doctor], ids=["detect", "doctor"])
@pytest.mark.parametrize("payload", [_DUPLICATE_OBJECT, _NON_FINITE_OBJECT])
def test_http_discovery_rejects_ambiguous_json(
    monkeypatch: pytest.MonkeyPatch,
    module: ModuleType,
    payload: bytes,
) -> None:
    monkeypatch.setattr(
        module,
        "open_no_redirect",
        lambda *_args, **_kwargs: _Response(payload),
    )

    assert module._http_get_json("https://models.invalid") is None


@pytest.mark.parametrize("payload", [_DUPLICATE_OBJECT, _NON_FINITE_OBJECT])
def test_config_wizard_rejects_ambiguous_model_inventory(payload: bytes) -> None:
    dependencies = WizardDependencies(open_url=lambda *_args, **_kwargs: _Response(payload))

    assert (
        _fetch_models_custom(
            "https://models.invalid/v1",
            dependencies=dependencies,
        )
        == []
    )


def _codex_transcript(model_payload: str) -> str:
    events = (
        {
            "type": "item.completed",
            "item": {"type": "agent_message", "text": model_payload},
        },
        {"type": "turn.completed"},
    )
    return "\n".join(json.dumps(event) for event in events)


@pytest.mark.parametrize(
    "payload",
    [
        '{"selected_ids":[],"selected_ids":["unsafe"],"confidence":1}',
        '{"selected_ids":[],"confidence":NaN}',
    ],
)
def test_cli_judges_reject_ambiguous_model_output(payload: str) -> None:
    assert _parse_codex(_codex_transcript(payload)) is None
    assert _parse_claude(json.dumps({"result": payload})) is None


def test_cli_judges_enforce_output_size_limit() -> None:
    oversized = json.dumps({"result": "x" * (64 * 1024)})

    assert _parse_claude(oversized) is None
    assert _parse_codex(oversized) is None


@pytest.mark.parametrize(
    "payload",
    ['{"ok":true,"ok":false}', '{"ok":NaN}'],
)
def test_tool_result_json_fails_closed(payload: str) -> None:
    assert _tool_failure_reason(payload) == "tool call returned invalid structured output"


@pytest.mark.parametrize(
    "payload",
    ['{"ok":true,"ok":false}', '{"ok":NaN}'],
)
def test_command_backend_rejects_ambiguous_json(payload: str) -> None:
    backend = CommandBackend(command=("unused",), output_format="json")

    with pytest.raises(ValueError, match="invalid bounded JSON output"):
        backend.parse_stdout(payload)


def test_command_backend_enforces_caller_output_limit() -> None:
    backend = CommandBackend(command=("unused",), output_format="json", max_output_chars=8)

    with pytest.raises(ValueError, match="configured limit"):
        backend.parse_stdout('{"value":1}')


def test_command_backend_rejects_ambiguous_jsonl_line() -> None:
    backend = CommandBackend(command=("unused",), output_format="jsonl")

    with pytest.raises(ValueError, match="line 2"):
        backend.parse_stdout('{"ok":true}\n{"ok":true,"ok":false}')


@pytest.mark.parametrize(
    "payload",
    ['{"registered":true,"registered":false}', '{"registered":NaN}'],
)
def test_native_inventory_rejects_ambiguous_json(payload: str) -> None:
    result = NativeCommandResult(("host", "plugins", "list"), 0, payload)

    assert _json_output(result) is None


@pytest.mark.parametrize(
    "payload",
    ['{"value":1,"value":2}', '{"value":NaN}'],
)
def test_canary_subprocess_parser_rejects_ambiguous_json(payload: str) -> None:
    with pytest.raises(ValueError):
        canary._load_canary_json(payload, maximum_bytes=1024)


def test_canary_subprocess_parser_enforces_output_limit() -> None:
    with pytest.raises(ValueError):
        canary._load_canary_json('{"value":1}', maximum_bytes=8)


@pytest.mark.parametrize(
    "payload",
    ['{"selected_ids":[],"selected_ids":["unsafe"]}', '{"confidence":NaN}'],
)
def test_model_response_parser_rejects_ambiguous_json(payload: str) -> None:
    assert judge.parse_json_response(payload) is None
    assert judge._read_json_object(_Response(payload.encode("utf-8"))) is None


def test_model_response_parser_enforces_output_limit() -> None:
    assert judge.parse_json_response("x" * (judge._MAX_JUDGE_RESPONSE_BYTES + 1)) is None


@pytest.mark.parametrize("payload", [_DUPLICATE_OBJECT, _NON_FINITE_OBJECT])
def test_smoke_manifest_parser_rejects_ambiguous_json(
    monkeypatch: pytest.MonkeyPatch,
    payload: bytes,
) -> None:
    monkeypatch.setattr(
        smoke,
        "read_bounded_regular_file",
        lambda *_args, **_kwargs: payload,
    )

    with pytest.raises(ValueError):
        smoke._load_plugin_json(Path("unused.json"), label="test manifest")


def test_persisted_roster_lists_reject_ambiguous_json() -> None:
    assert _decode_json_list('[{"value":1,"value":2}]') == []
    assert _decode_json_list("[NaN]") == []


def test_persisted_activity_rejects_ambiguous_json() -> None:
    finalizations: list[dict[str, Any]] = [{"missing": '[{"value":1,"value":2}]'}]
    routing: list[dict[str, Any]] = [{"selected_ids": '[{"value":1,"value":2}]'}]

    assert normalize_activity_rows("finalizations", finalizations)[0]["missing"] == ["unparseable"]
    assert normalize_activity_rows("routing", routing)[0]["selected_ids"] == []


def test_persisted_snapshot_rejects_ambiguous_json() -> None:
    snapshot = normalize_snapshot(
        {
            "manifest": '{"approved":true,"approved":false,"added":["unsafe"]}',
            "activated": 0,
        }
    )

    assert snapshot["approved"] is False
    assert snapshot["added"] == 0
