"""Branch-complete tests for chat-header and receipt truthfulness."""

from __future__ import annotations

import importlib
import sqlite3
from pathlib import Path

import pytest

import agency_runtime.core.header.contract as contract
import agency_runtime.core.receipts.normalize as receipts

finalizer = importlib.import_module("agency_runtime.core.header.finalize")


def _fields(**overrides: str) -> dict[str, str]:
    values = {
        "agencies_loaded": "none",
        "agencies_delegated": "none",
        "skills_loaded": "none",
        "actual_model_selected": "task-general -> unavailable",
        "why": "audit",
        "how_it_shaped_outcome": "made evidence visible",
    }
    values.update(overrides)
    return values


def test_header_cleaning_parsing_and_validation_edge_cases() -> None:
    assert contract._clean(None) == ""
    assert contract._clean(" first\nsecond ") == "first second"
    assert contract._is_present("<none>") is False
    assert contract._is_present("evidence") is True
    assert contract.parse_header("malformed\nUnknown: value\nWhy: valid") == {"why": "valid"}

    empty = contract.format_header(_fields(why=""))
    valid, missing = contract.validate_header(empty)
    assert valid is False
    assert missing == ["why"]

    out_of_order = empty.replace("Agency/Agencies loaded: none", "Wrong label: none", 1)
    valid, missing = contract.validate_header(out_of_order)
    assert valid is False
    assert missing[0] == "agencies_loaded"


def test_header_split_and_dedupe_cover_empty_and_duplicate_values() -> None:
    header = contract.format_header(_fields())

    assert contract._starts_with_header(header) is True
    assert contract._starts_with_header("body") is False
    lines, body = contract._split_header_body(header)
    assert len(lines) == 6
    assert body == ""
    lines, body = contract._split_header_body(header + "\n\nBody")
    assert len(lines) == 6
    assert body == "Body"
    assert contract._dedupe(["", " alpha ", "alpha", "beta\nline"]) == [
        "alpha",
        "beta line",
    ]


class _BrokenGetter:
    def get_specialists_for_session(self, _session_id: str) -> list[str]:
        raise RuntimeError("offline")

    def get_skills_for_session(self, _session_id: str) -> list[str]:
        raise RuntimeError("offline")


class _BrokenTraceGetter:
    def get_specialists_for_trace(self, *_args: str) -> list[str]:
        raise RuntimeError("offline")

    def get_delegations(self, *_args: str) -> list[dict[str, str]]:
        raise RuntimeError("offline")

    def get_skills_for_trace(self, *_args: str) -> list[str]:
        raise RuntimeError("offline")

    def get_model_receipt(self, *_args: str) -> dict[str, str]:
        raise RuntimeError("offline")


class _NoConnection:
    pass


class _BrokenConnection:
    def _connect(self) -> object:
        raise sqlite3.Error("offline")


class _FallbackSpecialists:
    def __init__(self, path: Path) -> None:
        self.path = path

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        return connection


def test_header_store_readers_fail_closed_and_support_legacy_connections(
    tmp_path: Path,
) -> None:
    assert contract._get_loaded_specialists(None, "s", "t") == []
    assert contract._get_loaded_specialists(_NoConnection(), "s", "t") == []
    assert contract._get_loaded_specialists(_BrokenGetter(), "s", "t") == []
    assert contract._get_loaded_specialists(_BrokenConnection(), "s", "t") == []
    assert contract._get_delegations(None, "s", "t") == []
    assert contract._get_delegations(_NoConnection(), "s", "t") == []
    assert contract._get_delegations(_BrokenConnection(), "s", "t") == []
    assert contract._get_skills(None, "s", "t") == []
    assert contract._get_skills(_NoConnection(), "s", "t") == []
    assert contract._get_skills(_BrokenGetter(), "s", "t") == []
    assert contract._latest_model_receipt(None, "s", "t") is None
    assert contract._latest_model_receipt(_NoConnection(), "s", "t") is None
    assert contract._latest_model_receipt(_BrokenConnection(), "s", "t") is None

    database = tmp_path / "legacy.db"
    connection = sqlite3.connect(database)
    try:
        connection.execute(
            "CREATE TABLE specialists_loaded (session_id TEXT, agent_slug TEXT, loaded_at TEXT)"
        )
        connection.executemany(
            "INSERT INTO specialists_loaded VALUES (?, ?, ?)",
            [("s", "reviewer", "1"), ("s", "reviewer", "2"), ("s", "", "3")],
        )
        connection.commit()
    finally:
        connection.close()
    # Pre-v11 session-only rows remain historical and cannot satisfy a turn.
    assert contract._get_loaded_specialists(_FallbackSpecialists(database), "s", "t") == []


@pytest.mark.parametrize(
    ("reader", "broken"),
    [
        (contract._get_loaded_specialists, _BrokenTraceGetter()),
        (contract._get_delegations, _BrokenTraceGetter()),
        (contract._get_skills, _BrokenTraceGetter()),
        (contract._latest_model_receipt, _BrokenTraceGetter()),
    ],
)
def test_header_store_readers_reject_unverifiable_authoritative_evidence(
    reader: object,
    broken: object,
) -> None:
    with pytest.raises(contract.EvidenceCorrelationError, match="could not be verified"):
        reader(broken, "s", "t", strict=True)  # type: ignore[operator]

    with pytest.raises(contract.EvidenceCorrelationError, match="could not be verified"):
        reader(_NoConnection(), "s", "t", strict=True)  # type: ignore[operator]


def test_header_model_and_delegation_lines_cover_truthful_outcomes() -> None:
    assert contract._complexity_for_model_group("task-implementation") == "implementation"
    assert contract._complexity_for_model_group("custom") == ""
    assert contract._model_line(None, "") == "unknown -> unavailable - no model receipt recorded"
    assert (
        contract._model_line({"requested_model": "task-general", "status": "timeout"}, "")
        == "[general] task-general -> timeout"
    )
    assert "no resolved model telemetry" in contract._model_line(
        {"requested_model": "task-general", "status": "success"}, ""
    )
    assert (
        contract._model_line(
            {
                "requested_model": "task-general",
                "resolved_model": "unavailable",
                "model_group": "production-router",
                "source": "litellm",
                "status": "success",
            },
            "",
        )
        == "[general] task-general -> unavailable - no resolved model telemetry "
        "via LiteLLM router production-router"
    )
    assert (
        contract._model_line(
            {
                "requested_model": "task-general",
                "model_group": "fallback-router",
                "source": "litellm",
                "status": "failed",
            },
            "",
        )
        == "[general] task-general -> failed via LiteLLM router fallback-router"
    )
    assert (
        contract._model_line(
            {
                "requested_model": "alias",
                "resolved_model": "actual",
                "resolved_provider": "provider",
                "model_group": "group",
                "source": "wrapper",
            },
            "",
        )
        == "alias -> provider/actual via group (wrapper)"
    )
    assert (
        contract._model_line({"requested_model": "alias", "resolved_model": "actual"}, "")
        == "alias -> actual (unknown)"
    )

    assert contract._delegation_line([]) == "none"
    assert (
        contract._delegation_line(
            [
                {
                    "recommended_agent": "reviewer",
                    "backend": "",
                    "status": "running",
                    "skip_reason": "",
                    "error": "",
                }
            ]
        )
        == "none - executed worker has no validated Agency specialist"
    )
    assert (
        contract._delegation_line(
            [
                {
                    "recommended_agent": "reviewer",
                    "backend": "test",
                    "status": "skipped",
                    "skip_reason": "backend unavailable",
                    "error": "",
                }
            ]
        )
        == "none - backend unavailable"
    )
    assert (
        contract._delegation_line([{"recommended_agent": "reviewer", "status": "suggested"}])
        == "none - delegation suggested but not executed"
    )


def test_fill_and_finalize_header_without_store_is_complete_and_idempotent() -> None:
    filled = contract.fill_header_fields({}, "", None, "task-general")
    assert filled["agencies_loaded"] == "none"
    assert filled["why"] == (
        "Unavailable - no authoritative explanation was recorded for this turn."
    )
    assert filled["how_it_shaped_outcome"] == (
        "Unavailable - no authoritative routing effect was recorded for this turn."
    )

    first = contract.finalize_header("\nBody", "", None, "task-general")
    second = contract.finalize_header(first, "", None, "task-general")
    assert second == first
    assert first.endswith("Body")


def test_header_explanations_humanize_live_routing_receipt_codes() -> None:
    why = contract.humanize_reason_codes(
        [
            "requested_question_task_or_output",
            "turn_kind:new_intent",
            "routing_status:policy_fallback",
            "inference_mode:heuristic",
            "eligibility:missing_capabilities",
            "eligibility:unsupported_tool_platform",
        ]
    )
    effect = contract.humanize_effect_codes(
        [
            "inference_attempted",
            "eligibility_exclusions_applied",
            "compatibility_constraints_applied",
            "specialists_selected",
            "policy_fallback_applied",
        ]
    )

    assert "substantive answer or action" in why
    assert "default coordinator policy" in why
    assert "required capabilities" in why
    assert "reason_codes=" not in why
    assert "Agency attempted inference" in effect
    assert "default coordinators" in effect
    assert "effect_codes=" not in effect


class _FinalizationRecorder:
    def __init__(self, *, fail: bool = False) -> None:
        self.fail = fail
        self.calls: list[dict[str, object]] = []

    def record_finalization(self, **kwargs: object) -> None:
        if self.fail:
            raise RuntimeError("storage offline")
        self.calls.append(kwargs)

    def commit_terminal_finalization(self, **kwargs: object) -> dict[str, object]:
        if self.fail:
            raise RuntimeError("storage offline")
        self.calls.append(kwargs)
        return {
            "outcome": "committed",
            "authoritative": True,
            "action": kwargs["action"],
            "response_hash": kwargs["response_hash"],
            "status": kwargs["status"],
        }

    def get_run(self, trace_id: str) -> dict[str, str] | None:
        return {"session_id": "s", "status": "active"} if trace_id == "t" else None

    def get_authoritative_finalization(
        self,
        _session_id: str,
        _trace_id: str,
        *,
        action: str,
        response_hash: str,
    ) -> None:
        del action, response_hash
        return None

    def get_completion_evidence_snapshot(
        self,
        session_id: str,
        trace_id: str,
    ) -> dict[str, object]:
        return {
            "session_id": session_id,
            "trace_id": trace_id,
            "status": "active",
            "request_kind": "trivial",
            "evidence_revision": 1,
            "run": {
                "session_id": session_id,
                "trace_id": trace_id,
                "status": "active",
                "request_kind": "trivial",
                "evidence_revision": 1,
            },
            "model_receipt": None,
            "skills": [],
            "specialists": [],
            "delegations": [],
        }

    def get_specialists_for_trace(self, _session_id: str, _trace_id: str) -> list[str]:
        return []

    def get_delegations(self, _trace_id: str) -> list[dict[str, str]]:
        return []

    def get_skills_for_trace(self, _session_id: str, _trace_id: str) -> list[str]:
        return []

    def get_model_receipt(self, _trace_id: str) -> None:
        return None

    def is_nontrivial_turn(self, _session_id: str, _trace_id: str) -> bool:
        return False


def test_finalization_empty_body_alias_and_recording_boundaries(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    recorder = _FinalizationRecorder()
    empty = finalizer.finalize_response(
        None,  # type: ignore[arg-type]
        trace_metadata={"session": "s", "trace": "t", "runtime": "codex"},
        store=recorder,
    )
    assert empty == {"action": "continue", "text": None, "missing": ["draft_text"]}
    assert recorder.calls[0]["host"] == "codex"

    header_only = contract.format_header(_fields())
    result = finalizer.finalize(
        header_only,
        {"session_id": "s", "trace_id": "t"},
        recorder,
    )
    assert result["action"] == "continue"
    assert result["missing"] == ["response_body"]
    complete = finalizer.finalize_response(
        header_only + "\n\nBody",
        {"session_id": "s", "trace_id": "t"},
        recorder,
    )
    assert complete["action"] == "accept"
    assert complete["text"].endswith("Body")
    assert finalizer._body_after_possible_header(header_only) == ""
    assert finalizer._body_after_possible_header(" body ") == "body"
    assert finalizer._clean(None) == ""

    finalizer._record_finalization(None, "t", "host", "accept", [])
    finalizer._record_finalization(recorder, "", "host", "accept", [])
    finalizer._record_finalization(_FinalizationRecorder(fail=True), "t", "host", "accept", [])

    monkeypatch.setattr(finalizer, "validate_header", lambda _text: (False, ["why"]))
    rewritten = finalizer.finalize_response(
        "Body",
        {"session_id": "s", "trace_id": "t"},
        recorder,
    )
    assert rewritten["action"] == "rewrite"
    assert rewritten["missing"] == ["why"]


@pytest.mark.parametrize(
    "value,expected",
    [(None, "fallback"), (" value ", "value"), (7, "7")],
)
def test_receipt_cleaning(value: object, expected: str) -> None:
    assert receipts._clean(value, "fallback") == expected


@pytest.mark.parametrize(
    "value,expected",
    [(None, 3), ("", 3), ("7", 7), (object(), 3), ("bad", 3)],
)
def test_receipt_integer_normalization(value: object, expected: int) -> None:
    assert receipts._int(value, 3) == expected


@pytest.mark.parametrize(
    "model_id,expected",
    [
        ("", ("", "")),
        ("custom/alias", ("", "")),
        ("model", ("", "model")),
        ("provider/model", ("provider", "model")),
        ("/model", ("", "")),
        ("provider/", ("", "")),
    ],
)
def test_receipt_model_id_parsing(model_id: str, expected: tuple[str, str]) -> None:
    assert receipts._provider_model_from_model_id(model_id) == expected


@pytest.mark.parametrize(
    "api_base,expected",
    [
        ("", ""),
        ("not a host", ""),
        ("https://api.openai.com/v1", "openai"),
        ("https://api.anthropic.com", "anthropic"),
        ("https://api.groq.com", "groq"),
        ("https://api.mistral.ai", "mistral"),
        ("https://openrouter.ai", "openrouter"),
        ("https://example.azure.com", "azure"),
        ("http://localhost:11434", "local"),
        ("https://models.example.test", "models.example.test"),
    ],
)
def test_receipt_provider_inference(api_base: str, expected: str) -> None:
    assert receipts._provider_from_api_base(api_base) == expected


def test_canonical_receipt_sanitizes_aliases_defaults_and_invalid_values() -> None:
    receipt = receipts._canonical_receipt(
        host="",
        source="invented",
        resolved_model="custom/alias",
        resolved_provider="custom/provider",
        attempted_fallbacks="bad",
        status="",
        started_at="",
        ended_at="",
        ignored="value",
    )

    assert receipt["host"] == "unknown"
    assert receipt["source"] == "unknown"
    assert receipt["resolved_model"] == "unavailable"
    assert receipt["resolved_provider"] == ""
    assert receipt["attempted_fallbacks"] == 0
    assert receipt["status"] == "unknown"
    assert receipt["started_at"]
    assert receipt["ended_at"]
    assert "ignored" not in receipt

    assert receipts._canonical_receipt(resolved_provider="CUSTOM")["resolved_provider"] == ""


def test_litellm_and_host_receipts_cover_unknown_and_inferred_truth() -> None:
    unknown = receipts.normalize_litellm_receipt({}, "alias")
    assert unknown["source"] == "unknown"
    assert unknown["resolved_model"] == "unavailable"

    local = receipts.normalize_litellm_receipt(
        {
            "x-litellm-model-api-base": "http://127.0.0.1:11434",
            "x-litellm-model-id": "ollama/model",
        },
        "alias",
    )
    assert local["resolved_provider"] == "local"
    assert local["model_id"] == "ollama/model"
    assert local["resolved_model"] == "unavailable"

    inferred = receipts.normalize_host_receipt(
        {
            "trace": "t",
            "runtime": "codex",
            "session": "s",
            "requested": "alias",
            "actual_model_id": "provider/model",
            "base_url": "https://models.example.test",
            "fallbacks": "2",
            "source": "invalid",
            "start_time": "start",
            "end_time": "end",
        }
    )
    assert inferred["resolved_provider"] == "provider"
    assert inferred["resolved_model"] == "model"
    assert inferred["source"] == "host"
    assert inferred["attempted_fallbacks"] == 2

    absent = receipts.normalize_host_receipt(None)
    assert absent["source"] == "unknown"
    assert absent["status"] == "unknown"


def test_receipt_first_and_unavailable_reason() -> None:
    assert receipts._first({"a": "", "b": "value"}, "a", "b") == "value"
    assert receipts._first({}, "missing", default="fallback") == "fallback"
    unavailable = receipts.build_unavailable_receipt("alias", None)  # type: ignore[arg-type]
    assert unavailable["model_id"] == ""
