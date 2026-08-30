"""Tests for the deterministic host-parity evaluation harness."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from agency_runtime.adapters.hooks import HookBridge
from agency_runtime.cli.main import main
from agency_runtime.core.evals import host_parity as host_parity_eval
from agency_runtime.core.evals.host_parity import _require, run_host_parity_eval
from agency_runtime.core.store.sqlite import Store


def test_host_parity_eval_harness_passes_core_contracts() -> None:
    report = run_host_parity_eval()

    assert report["suite"] == "host-parity"
    assert report["passed"] is True
    names = {case["name"] for case in report["cases"]}
    assert {
        "detect_numbered_list",
        "detect_status_query_no_delegate",
        "all_adapters_track_evidence",
        "all_adapters_capture_model_receipts",
        "cards_expire_with_their_turn",
    } <= names


def test_cards_do_not_survive_the_turn_that_loaded_them_on_every_adapter() -> None:
    """Rule 7 on every supported host: the card returns to the cabinet at turn end.

    ZCode is included by asking the hooks boundary for its adapter, because
    that is how zcode really reaches Agency; `generic` stands for any host with
    no dedicated adapter at all.
    """

    detail = host_parity_eval._case_cards_expire_with_their_turn()

    assert detail["hosts"] == [
        "hermes",
        "openclaw",
        "codex",
        "claude",
        "zcode",
        "generic",
    ]


def test_zcode_parity_is_observed_through_the_hook_boundarys_own_adapter(
    tmp_path: Path,
) -> None:
    """ZCode owns no adapter class, so the sweep must not invent one for it.

    The hooks boundary is where zcode's identity is decided. Were the eval to
    build its own zcode-shaped adapter, the sweep could go on reporting parity
    after that boundary changed underneath it.
    """

    store = Store(tmp_path / "agency.db")
    [(_, build)] = [entry for entry in host_parity_eval._PARITY_ADAPTERS if entry[0] == "zcode"]

    swept = build(store)
    boundary = HookBridge("zcode", store=store).adapter

    assert swept.host_name == "zcode"
    assert boundary.host_name == "zcode"
    assert type(swept) is type(boundary)


def test_parity_sweep_refuses_an_adapter_that_is_not_the_host_it_claims(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A builder that returns a neighbour must fail, not be reported as parity."""

    monkeypatch.setattr(
        host_parity_eval,
        "hook_host_adapter",
        lambda _host, store: host_parity_eval.ClaudeAdapter(store=store),
    )

    with pytest.raises(AssertionError, match="while claiming 'zcode'"):
        host_parity_eval._case_cards_expire_with_their_turn()


def test_card_expiry_eval_fails_when_a_card_survives_into_the_next_turn(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The case must be able to fail; a always-empty next turn proves nothing."""

    monkeypatch.setattr(
        host_parity_eval.Store,
        "get_specialists_for_trace",
        lambda *_args: ["software-architect"],
    )

    with pytest.raises(AssertionError, match="carried into the next turn"):
        host_parity_eval._case_cards_expire_with_their_turn()


def test_host_parity_eval_owns_its_master_switch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A deterministic eval must not change result when an operator runs `agency off`.

    The adapters read the operator's durable control by default, so without an
    explicitly bound root this suite silently reported evidence mismatches
    whenever Agency was disabled on the machine running it.
    """

    # Model the real situation rather than a switch that is off everywhere:
    # the operator's durable control says disabled, and only a caller-owned
    # root says enabled. Patching without honouring `home_dir` would defeat
    # the very override under test.
    monkeypatch.setattr(
        "agency_runtime.core.runtime_control.master_enabled",
        lambda **kwargs: kwargs.get("home_dir") is not None,
    )

    report = run_host_parity_eval()

    assert report["passed"] is True


def test_cli_eval_host_parity_json(capsys) -> None:
    code = main(["eval", "host-parity", "--json"])

    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["suite"] == "host-parity"
    assert payload["passed"] is True


def test_eval_requirement_is_not_an_optimization_sensitive_assert() -> None:
    with pytest.raises(AssertionError, match="durable check"):
        _require(False, "durable check")


def test_eval_helpers_cover_authoritative_default_and_case_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fields = {
        "agencies_loaded": "none",
        "agencies_delegated": "none",
        "skills_loaded": "none",
        "actual_model_selected": "unknown -> unavailable - no model receipt recorded",
        "why": "reason_codes=test",
        "how_it_shaped_outcome": "effect_codes=test",
    }
    monkeypatch.setattr(
        host_parity_eval,
        "fill_header_fields",
        lambda *_args, **_kwargs: dict(fields),
    )
    assert host_parity_eval._header(object()) == host_parity_eval.format_header(fields)

    failed = host_parity_eval._run_case(
        "expected-failure",
        lambda: _require(False, "bounded failure"),
    )
    assert failed == {
        "name": "expected-failure",
        "passed": False,
        "error": "bounded failure",
    }


def test_model_receipt_eval_fails_when_adapter_records_nothing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(host_parity_eval.Store, "get_model_receipt", lambda *_args: None)

    with pytest.raises(AssertionError, match="model receipt is missing"):
        host_parity_eval._case_all_adapters_capture_model_receipts()


def test_eval_requirement_survives_real_optimized_interpreter() -> None:
    script = """
from agency_runtime.core.evals.host_parity import _require

try:
    _require(False, "durable optimized check")
except AssertionError:
    raise SystemExit(0)
raise SystemExit(17)
"""
    # Fixed local interpreter and static source; no shell or caller input.
    completed = subprocess.run(
        [sys.executable, "-O", "-c", script],
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
