"""AR-355: what Agency's frame costs per turn, measured from the rendering code.

The per-turn token cost of the working-agreements addition was the one open
AR-355 box. These tests pin the estimator labelling, the component sizing
(rendered with the same code a host receives), the AR-355 delta, the fail-open
shape after AR-356/AR-367, the staffed-capsule replay from a real ready turn,
and the CLI surface.
"""

from __future__ import annotations

import argparse
import dataclasses
import hashlib
import io
import json
from contextlib import redirect_stdout
from pathlib import Path
from typing import Any

import pytest

from agency_runtime.cli import evidence_commands
from agency_runtime.core.config import AgencyConfig
from agency_runtime.core.context_budget import (
    CHARS_PER_TOKEN_HEURISTIC,
    RESIDENT_KERNEL_V5_ADDITION,
    TOKEN_ESTIMATOR_HEURISTIC,
    context_budget_report,
    heuristic_token_count,
    measure_component,
    measure_staffed_capsules,
    token_estimator,
)
from agency_runtime.core.fail_open_disclosure import FAIL_OPEN_DISCLOSURE_MARKER
from agency_runtime.core.host_capabilities import native_adapter_capability_receipt
from agency_runtime.core.operator_policy import OPERATOR_POLICY_HEADER
from agency_runtime.core.preflight import run_preflight
from agency_runtime.core.resident_managers import RESIDENT_MANAGER_KERNEL
from agency_runtime.core.store.sqlite import Store
from agency_runtime.core.turn_origin import native_adapter_turn_origin

POLICY = "1. Prefer small reviewable changes.\n2. Cite the receipt id.\n3. Never guess."


def test_heuristic_estimator_is_ceil_chars_over_four_and_labelled() -> None:
    assert heuristic_token_count("") == 0
    assert heuristic_token_count("abcd") == 1
    assert heuristic_token_count("abcde") == 2
    estimator = token_estimator("chars")
    assert estimator.method == TOKEN_ESTIMATOR_HEURISTIC
    assert estimator.estimate("x" * (CHARS_PER_TOKEN_HEURISTIC * 3 + 1)) == 4
    injected = token_estimator(tokenizer=lambda text: len(text.split()))
    assert injected.method == "injected"
    assert injected.estimate("three short words") == 3
    with pytest.raises(ValueError, match="auto, chars, or tiktoken"):
        token_estimator("words")


def test_measure_component_sizes_text_exactly_as_delivered() -> None:
    component = measure_component("sample", "a\nb\nc", token_estimator("chars"), note="n")
    assert component.as_dict() == {
        "name": "sample",
        "chars": 5,
        "lines": 3,
        "estimated_tokens": 2,
        "note": "n",
    }
    assert measure_component("empty", "", token_estimator("chars")).lines == 0


def test_report_isolates_the_ar355_delta_and_the_fail_open_shape() -> None:
    config = dataclasses.replace(AgencyConfig(), operator_policy=POLICY)
    estimator = token_estimator("chars")

    report = context_budget_report(config, host="claude", estimator=estimator)

    assert report["estimator"]["method"] == TOKEN_ESTIMATOR_HEURISTIC
    assert report["kernel"]["version"] == 5
    assert report["kernel"]["chars"] == len(RESIDENT_MANAGER_KERNEL)
    assert RESIDENT_KERNEL_V5_ADDITION in RESIDENT_MANAGER_KERNEL
    components = report["components"]
    assert components["resident_kernel"]["chars"] == len(RESIDENT_MANAGER_KERNEL)
    assert components["operator_policy_block"]["chars"] > len(POLICY)
    assert components["fail_open_disclosure"]["lines"] == 1
    delta = report["ar355_delta"]
    policy_block = components["operator_policy_block"]["chars"]
    assert delta["kernel_v5_addition"]["chars"] == len(RESIDENT_KERNEL_V5_ADDITION) + 1
    assert delta["operator_policy_block"]["policy_text_chars"] == len(POLICY)
    assert delta["per_ready_turn"]["chars"] == (
        delta["kernel_v5_addition"]["chars"] + 2 + policy_block
    )
    assert delta["per_fail_open_turn"]["chars"] == delta["per_ready_turn"]["chars"]
    turns = report["per_turn"]
    assert turns["fail_open_turn"]["components"] == [
        "resident_kernel",
        "resident_binding_reference",
        "operator_policy_block",
        "fail_open_disclosure",
        "header_snapshot_initial",
    ]
    assert turns["fail_open_turn"]["carries_operator_policy"] is True
    assert "resident_kernel" not in turns["fail_open_turn_reused_binding"]["components"]
    assert (
        turns["fail_open_turn_reused_binding"]["chars"]
        == turns["fail_open_turn"]["chars"] - len(RESIDENT_MANAGER_KERNEL) - 2
    )
    staffed = turns["staffed_turn"]
    assert staffed["chars"] is None and staffed["bound_chars"] > 0
    assert report["staffed_capsule"]["measured"] is False


def test_report_without_policy_or_snapshot_host_drops_those_components() -> None:
    report = context_budget_report(
        AgencyConfig(), host="hermes", estimator=token_estimator("chars")
    )
    assert report["components"]["operator_policy_block"]["chars"] == 0
    assert (
        report["ar355_delta"]["per_ready_turn"]["chars"]
        == (report["ar355_delta"]["kernel_v5_addition"]["chars"])
    )
    assert report["per_turn"]["fail_open_turn"]["fixed_chars"] == (
        len(RESIDENT_MANAGER_KERNEL)
        + 2
        + report["components"]["resident_binding_reference"]["chars"]
        + 2
        + report["components"]["fail_open_disclosure"]["chars"]
    )
    assert OPERATOR_POLICY_HEADER not in POLICY  # the policy text itself carries no framing


def test_staffed_capsules_are_replayed_from_a_real_ready_turn(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from agency_runtime.core.selector import pipeline
    from agency_runtime.core.selector.delegation_detection import detect_work_units

    store = Store(tmp_path / "capsules.db")
    assert measure_staffed_capsules(store, AgencyConfig())["reason"] == "no ready turn in the store"
    store._activate_prevalidated_agent(
        {
            "slug": "budget-reviewer",
            "name": "Budget Reviewer",
            "description": "Reviews with a bounded budget.",
            "version": "1.0",
            "prompt_body": "Review the bounded request carefully.\n" * 20,
        }
    )
    receipt = native_adapter_capability_receipt(
        "codex", platform="linux", session_id="budget-session", trace_id="budget-turn"
    )

    def route(
        _session_id: str,
        user_message: str,
        _catalog: list[dict[str, object]] | None = None,
        **kwargs: object,
    ) -> dict[str, object]:
        return {
            "trace_id": str(kwargs.get("trace_id") or "budget-turn"),
            "selected_ids": ["budget-reviewer"],
            "confidence": 0.99,
            "status": "applied",
            "source": "test",
            "query_hash": hashlib.sha256(user_message.encode()).hexdigest(),
            "context_fingerprint": "c" * 64,
            "work_units": detect_work_units(user_message),
            "execution_context": receipt.as_dict(),
        }

    monkeypatch.setattr(pipeline, "route", route)
    run_preflight(
        store,
        session_id="budget-session",
        trace_id="budget-turn",
        user_message="Review this code for correctness",
        host="codex",
        capability_receipt=receipt,
        origin_receipt=native_adapter_turn_origin(
            "external_user",
            host="codex",
            event="adapter_preflight",
            session_id="budget-session",
            trace_id="budget-turn",
        ),
    )

    measured = measure_staffed_capsules(store, AgencyConfig(), estimator=token_estimator("chars"))

    assert measured["measured"] is True
    assert measured["staffed_replayed"] == 1
    assert measured["specialist_capsule_chars"]["p50"] > 0
    assert measured["specialists_per_staffed_turn"]["max"] == 1
    report = context_budget_report(
        AgencyConfig(), host="codex", estimator=token_estimator("chars"), capsules=measured
    )
    staffed = report["per_turn"]["staffed_turn"]
    assert staffed["capsule_p50_chars"] == measured["specialist_capsule_chars"]["p50"]
    assert staffed["chars"] == staffed["fixed_chars"] + 2 + staffed["capsule_p50_chars"]


def test_cli_prints_the_budget_and_json(tmp_path: Path) -> None:
    Store(tmp_path / "empty.db")
    args = argparse.Namespace(
        host="claude", sample=None, estimator="chars", db=str(tmp_path / "empty.db"), json=False
    )
    text = io.StringIO()
    with redirect_stdout(text):
        assert evidence_commands.cmd_evidence_context_budget(args) == 0
    human = text.getvalue()
    assert "context budget for host claude (chars/4)" in human
    assert "resident_kernel" in human
    assert "AR-355 delta per ready turn" in human
    assert "not measured (no ready turn in the store)" in human

    args.json = True
    payload = io.StringIO()
    with redirect_stdout(payload):
        assert evidence_commands.cmd_evidence_context_budget(args) == 0
    parsed: dict[str, Any] = json.loads(payload.getvalue())
    assert parsed["host"] == "claude"
    assert FAIL_OPEN_DISCLOSURE_MARKER.startswith("[Agency staffing failed")
    assert parsed["components"]["fail_open_disclosure"]["chars"] > 0
    assert parsed["staffed_capsule"]["measured"] is False
