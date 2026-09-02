"""AR-357: the response contract is stated once per turn and never drifts.

Two measured claude-host failures drive these tests. On 2026-09-01 a
substantive response that followed the newest snapshot verbatim was withheld
with ``response_invalid, missing: ["evidence_verification"]`` -- a requirement
the model was never given, produced by Agency failing to read its own evidence.
The same evening a turn received no snapshot at all, reused the previous turn's
header, and was withheld with a fixed sentence that named nothing.

So: the canonical statement is hash-pinned and delivered once beside the turn's
first values; every later snapshot says it carries values only; a turn whose
snapshot cannot render is told so instead of being left silent; a rejection
names only requirements the contract stated; and unreadable evidence publishes
unverified rather than being reported as a missing requirement.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from agency_runtime.core.header.contract import (
    DELIVERED_REQUIREMENTS,
    HEADER_FIELDS,
    VERIFIER_EVIDENCE_CODES,
    requirement_labels,
    split_missing_requirements,
    verification_is_unavailable,
)
from agency_runtime.core.header.finalize import (
    TERMINAL_OUTCOME_MESSAGES,
    finalize_response,
    stored_missing_requirements,
    terminal_rejection_reason,
)
from agency_runtime.core.header.response_contract import (
    RESPONSE_CONTRACT_MARKER,
    RESPONSE_CONTRACT_SHA256,
    RESPONSE_CONTRACT_TEXT,
    SNAPSHOT_VALUES_ONLY_NOTE,
    header_snapshot_unavailable_context,
    response_contract_context,
)
from agency_runtime.core.header.snapshot import HEADER_SNAPSHOT_INSTRUCTIONS

_REPOSITORY = Path(__file__).parents[1]


def _run_hook(host: str, db_path: Path, payload: dict[str, object]) -> dict[str, object]:
    runtime_control_path = db_path.parent / ".agency-runtime" / "run" / "control.json"
    env = os.environ.copy()
    env["AGENCY_CANARY_MODE"] = "1"
    env["AGENCY_CANARY_CONTROL_PATH"] = str(runtime_control_path)
    env.pop("AGENCY_CANARY_REQUIRE_EXISTING_STORE", None)
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "agency_runtime.cli",
            "hook",
            host,
            "--db",
            str(db_path),
            "--runtime-control",
            str(runtime_control_path),
        ],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        cwd=_REPOSITORY,
        env=env,
        timeout=60,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    return json.loads(completed.stdout or "{}")


def _prompt_context(host: str, db_path: Path, session_id: str, turn_id: str) -> str:
    result = _run_hook(
        host,
        db_path,
        {
            "hook_event_name": "UserPromptSubmit",
            "session_id": session_id,
            "turn_id": turn_id,
            "model": "gpt-5.6-codex",
            "prompt": "agency status",
        },
    )
    output = result.get("hookSpecificOutput")
    assert isinstance(output, dict)
    return str(output["additionalContext"])


def test_the_contract_text_is_pinned_and_states_only_what_is_verified() -> None:
    assert RESPONSE_CONTRACT_TEXT.startswith(f"{RESPONSE_CONTRACT_MARKER}\n")
    # The pin fails loudly if the wording changes, because the wording is a
    # claim about what validate_completion_policy checks.
    assert (
        RESPONSE_CONTRACT_SHA256
        == "81e3be06905a637098e7ae0892bd7b8285ef39b1265acedd846cfbf39deab773"
    )
    assert response_contract_context() == RESPONSE_CONTRACT_TEXT
    for _key, label in HEADER_FIELDS:
        assert label in RESPONSE_CONTRACT_TEXT
    assert f"these {len(HEADER_FIELDS)} lines" in RESPONSE_CONTRACT_TEXT
    # No promise the verifier does not keep: the pre-AR-357 hermes instruction
    # claimed seven lines while the verifier checked five.
    assert "seven lines" not in RESPONSE_CONTRACT_TEXT
    assert "publishes unverified" in RESPONSE_CONTRACT_TEXT


def test_every_snapshot_instruction_says_it_carries_values_only() -> None:
    assert set(HEADER_SNAPSHOT_INSTRUCTIONS) == {"INITIAL", "UPDATED", "FINAL"}
    for instruction in HEADER_SNAPSHOT_INSTRUCTIONS.values():
        assert SNAPSHOT_VALUES_ONLY_NOTE in instruction
        assert "supersedes" not in instruction


def test_missing_vocabulary_splits_delivered_requirements_from_agency_faults() -> None:
    delivered, other = split_missing_requirements(
        ["agencies_loaded", "evidence_verification", "agencies_loaded", "", 7, "correlation"]
    )
    assert delivered == ["agencies_loaded"]
    assert other == ["evidence_verification", "correlation"]
    assert split_missing_requirements("agencies_loaded") == ([], [])
    assert set(VERIFIER_EVIDENCE_CODES) <= {"evidence_verification", "specialist_activation"}
    assert "response_body" in DELIVERED_REQUIREMENTS

    for code in VERIFIER_EVIDENCE_CODES:
        assert verification_is_unavailable([code]) is True
    assert verification_is_unavailable(["evidence_verification", "agencies_loaded"]) is False
    assert verification_is_unavailable(["correlation"]) is False
    assert verification_is_unavailable([]) is False


def test_a_rejection_names_only_requirements_the_contract_stated() -> None:
    labels = requirement_labels(["agencies_loaded", "skills_loaded", "evidence_verification"])
    assert labels == ["Agency/Agencies loaded", "Skills loaded"]
    assert requirement_labels(["response_body"]) == ["a non-empty body"]
    # Header order, not the order the verifier happened to report.
    assert requirement_labels(["recruited_via", "agencies_loaded"]) == [
        "Agency/Agencies loaded",
        "Recruited via",
    ]

    reason = terminal_rejection_reason("response_invalid", ["skills_loaded"])
    assert reason.startswith(TERMINAL_OUTCOME_MESSAGES["response_invalid"])
    assert reason.endswith("Unmet [AGENCY RESPONSE CONTRACT v1] lines: Skills loaded.")
    # An Agency-side code names nothing; the operator is never told they failed
    # a requirement they were not given.
    assert (
        terminal_rejection_reason("response_invalid", ["evidence_verification"])
        == TERMINAL_OUTCOME_MESSAGES["response_invalid"]
    )
    assert (
        terminal_rejection_reason("response_invalid")
        == (TERMINAL_OUTCOME_MESSAGES["response_invalid"])
    )
    assert terminal_rejection_reason("nonexistent_action", ["skills_loaded"]) == ""


def test_a_replayed_rejection_names_the_same_lines_as_the_original() -> None:
    assert stored_missing_requirements('["skills_loaded", "recruited_via"]') == [
        "skills_loaded",
        "recruited_via",
    ]
    assert stored_missing_requirements(["skills_loaded", 3]) == ["skills_loaded"]
    assert stored_missing_requirements(None) == []
    assert stored_missing_requirements("not json") == []
    assert stored_missing_requirements('{"skills_loaded": true}') == []
    assert stored_missing_requirements("[" + '"x",' * 5000 + '"y"]') == []


class _UnreadableEvidenceStore:
    """A store whose completion-evidence read fails the way the live one did."""

    def __init__(self, message: str) -> None:
        self._message = message

    def get_authoritative_finalization(self, *_args: object, **_kwargs: object) -> None:
        return None

    def get_completion_evidence_snapshot(self, *_args: object, **_kwargs: object) -> object:
        raise ValueError(self._message)


@pytest.mark.parametrize(
    "message",
    [
        "selected specialist activation evidence is invalid",
        "completion evidence snapshot could not be verified",
    ],
)
def test_unreadable_evidence_publishes_unverified_instead_of_naming_a_requirement(
    message: str,
) -> None:
    """The measured 2026-09-01 shape: missing=['evidence_verification']."""

    result = finalize_response(
        "A substantive answer.",
        {
            "session_id": "ar357-unreadable",
            "trace_id": "ar357-unreadable-turn",
            "host": "claude",
        },
        _UnreadableEvidenceStore(message),
        "claude-opus-5",
    )

    assert result["action"] == "continue"
    assert result["missing"] == []
    assert result.get("verification_unavailable") is True
    assert result["text"] == "A substantive answer."


def test_a_correlation_failure_keeps_its_precise_code() -> None:
    """The store answering "this is not your turn" is a verdict, not blindness."""

    result = finalize_response(
        "A substantive answer.",
        {
            "session_id": "ar357-correlation",
            "trace_id": "ar357-correlation-turn",
            "host": "claude",
        },
        _UnreadableEvidenceStore("trace_id does not belong to session_id"),
        "claude-opus-5",
    )

    assert result["action"] == "continue"
    assert result["missing"] == ["correlation"]
    assert result.get("verification_unavailable") is not True


@pytest.mark.parametrize("host", ["codex", "zcode"])
def test_the_contract_is_delivered_once_beside_the_turns_first_values(
    host: str,
    tmp_path: Path,
) -> None:
    db_path = tmp_path / f"{host}-contract.db"
    context = _prompt_context(host, db_path, f"{host}-contract", f"{host}-contract-turn")

    assert context.count(RESPONSE_CONTRACT_MARKER) == 1
    assert RESPONSE_CONTRACT_TEXT in context
    assert "[AGENCY INITIAL HEADER SNAPSHOT v1]" in context
    assert context.index(RESPONSE_CONTRACT_MARKER) < context.index(
        "[AGENCY INITIAL HEADER SNAPSHOT v1]"
    )
    assert SNAPSHOT_VALUES_ONLY_NOTE in context


def test_a_turn_whose_snapshot_cannot_render_is_told_so() -> None:
    """The second measured shape: no snapshot delivered, prior header reused."""

    unavailable = header_snapshot_unavailable_context("INITIAL")
    assert unavailable.startswith("[AGENCY INITIAL HEADER SNAPSHOT v1]\n")
    assert "Do not reuse header values from an earlier turn" in unavailable
    assert "publishes unverified" in unavailable
    assert header_snapshot_unavailable_context("UPDATED", version="v2").startswith(
        "[AGENCY UPDATED HEADER SNAPSHOT v2]\n"
    )
