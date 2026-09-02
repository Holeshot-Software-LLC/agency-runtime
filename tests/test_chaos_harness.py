"""AR-362: the agent-chaos harness injects owned faults and judges them.

Reliability evidence used to be observational; these tests pin that the two
shipped experiments reproduce the AR-353 staffing-window shape and the
runner hard-kill shape on demand inside a dedicated, rolled-back runtime,
that the safety envelope refuses live user turns and the live database in
code, that a raising effect or oracle is a failed receipt rather than a
crashed harness, and that every run seals an owner-private receipt.
"""

from __future__ import annotations

import io
import json
import stat
from contextlib import contextmanager, redirect_stdout
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from agency_runtime.core.chaos import (
    CHAOS_EXPERIMENT_NAMES,
    CHAOS_RECEIPT_SCHEMA,
    CHAOS_REPORT_SCHEMA,
    CHAOS_SESSION_PREFIX,
    CHAOS_SUMMARY_SCHEMA,
    RUNNER_HARD_KILL,
    STAFFING_WINDOW,
    VERDICT_FAIL,
    VERDICT_PASS,
    ChaosSafetyError,
    Effect,
    Experiment,
    Oracle,
    Safety,
    Verdict,
    chaos_report_summary,
    project_chaos_receipt,
    resolve_experiments,
    run_chaos_cli,
    run_chaos_experiments,
    run_experiment,
    staffing_shapes,
    write_chaos_receipt,
)
from agency_runtime.core.chaos import runner as chaos_runner
from agency_runtime.core.chaos import safety as chaos_safety


@pytest.fixture(autouse=True)
def _plain_receipt_directories(monkeypatch: pytest.MonkeyPatch) -> None:
    """Receipts land under pytest's tmp_path, whose chain is not owner-private."""

    def _mkdir(path: Path) -> Path:
        Path(path).mkdir(parents=True, exist_ok=True)
        return Path(path)

    monkeypatch.setattr(chaos_runner, "ensure_private_directory", _mkdir)


def _quiet_oracle(name: str = "quiet") -> Oracle:
    return Oracle(name, "always passes", lambda _observations: Verdict(VERDICT_PASS))


@contextmanager
def _noop_effect_apply(_envelope: Any, _case: Any):
    yield {"applied": True}


def test_the_shipped_experiments_pass_against_shipped_behaviour(tmp_path: Path) -> None:
    report = run_chaos_experiments(receipt_root=tmp_path / "receipts")

    assert report["schema"] == CHAOS_REPORT_SCHEMA
    assert report["passed"] is True
    assert set(report["experiments"]) == set(CHAOS_EXPERIMENT_NAMES)
    staffing = report["experiments"][STAFFING_WINDOW.name]
    assert staffing["verdict"] == VERDICT_PASS
    assert staffing["cases"] == [shape.name for shape in staffing_shapes()]
    assert staffing["effect_applied"] is True
    hard_kill = report["experiments"][RUNNER_HARD_KILL.name]
    assert hard_kill["verdict"] == VERDICT_PASS
    # The recovery oracle passes by recording the current behaviour, gap and all.
    assert any("active" in note for note in hard_kill["gap_notes"])
    for detail in report["experiments"].values():
        receipt_path = Path(detail["receipt_path"])
        assert receipt_path.is_file()
        assert stat.S_IMODE(receipt_path.stat().st_mode) == 0o600
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        assert receipt["schema"] == CHAOS_RECEIPT_SCHEMA
        assert project_chaos_receipt(receipt) is not None
        assert receipt["safety"]["dedicated_store"] is True
        assert receipt["safety"]["runtime_home_removed"] is True
        assert all(session.startswith(CHAOS_SESSION_PREFIX) for session in receipt["session_ids"])


def test_staffing_window_covers_the_three_measured_shapes() -> None:
    names = [shape.name for shape in staffing_shapes()]
    assert names == ["provider_timeout", "invalid_completion", "critic_rejected"]
    codes = {code for shape in staffing_shapes() for code in shape.expected_staffing_codes}
    assert {"inference_unavailable", "inference_invalid", "staffing_critic_rejected"} <= codes


def test_safety_refuses_the_live_database_and_foreign_sessions(tmp_path: Path) -> None:
    safety = Safety()
    with safety.arm("envelope_probe") as envelope:
        home = envelope.runtime_home
        assert home.is_dir()
        minted = envelope.mint_session_id("probe")
        assert minted.startswith(CHAOS_SESSION_PREFIX)
        assert envelope.require_session(minted) == minted
        with pytest.raises(ChaosSafetyError, match="dedicated chaos sessions"):
            envelope.require_session("owner-telegram-session")
        for live in envelope.live_database_paths:
            with pytest.raises(ChaosSafetyError, match="never open the live"):
                envelope.open_store(live)
        with pytest.raises(ChaosSafetyError, match="only under the dedicated runtime home"):
            envelope.open_store(tmp_path / "elsewhere.db")
        store = envelope.open_store()
        assert Path(store.db_path).is_relative_to(home)
    assert not home.exists()


def test_effects_apply_only_inside_an_armed_envelope(tmp_path: Path) -> None:
    safety = Safety()
    with safety.arm("gate_probe") as envelope:
        envelope.require_armed()
    with pytest.raises(ChaosSafetyError, match="armed chaos envelope"):
        envelope.require_armed()


def test_a_raising_effect_is_a_failed_receipt_and_still_rolls_back() -> None:
    @contextmanager
    def _explode(_envelope: Any, _case: Any):
        raise PermissionError("owned adapter refused")
        yield  # pragma: no cover - never reached

    experiment = Experiment(
        "exploding_effect",
        "the effect refuses to apply",
        Effect("refusing_effect", "raises on apply", _explode),
        Safety(),
        _quiet_oracle(),
        lambda _envelope, _case, _detail: {"reached": True},
    )

    receipt = run_experiment(experiment)

    assert receipt.verdict.outcome == VERDICT_FAIL
    assert receipt.verdict.reason_codes == ("experiment_raised_permission_error",)
    assert receipt.effect_applied is False
    assert receipt.safety["runtime_home_removed"] is True


def test_a_raising_oracle_is_a_failed_receipt_not_a_crash() -> None:
    def _bad_judge(_observations: Any) -> Verdict:
        raise ValueError("observations unreadable")

    experiment = Experiment(
        "exploding_oracle",
        "the oracle cannot judge",
        Effect("noop_effect", "does nothing", _noop_effect_apply),
        Safety(),
        Oracle("bad_oracle", "raises", _bad_judge),
        lambda _envelope, _case, _detail: {"reached": True},
    )

    receipt = run_experiment(experiment)

    assert receipt.verdict.outcome == VERDICT_FAIL
    assert receipt.verdict.reason_codes == ("oracle_raised_validation_error",)
    assert receipt.effect_applied is True


def test_actions_see_only_chaos_sessions_and_the_dedicated_store() -> None:
    seen: dict[str, Any] = {}

    def _action(envelope: Any, _case: Any, detail: Any) -> dict[str, Any]:
        seen["session"] = envelope.mint_session_id("action")
        store = envelope.open_store()
        seen["db"] = str(store.db_path)
        seen["home"] = str(envelope.runtime_home)
        return {"identities": {"session_ids": [seen["session"]]}, "detail": dict(detail)}

    experiment = Experiment(
        "session_probe",
        "records what an action may touch",
        Effect("noop_effect", "does nothing", _noop_effect_apply),
        Safety(),
        _quiet_oracle(),
        _action,
    )

    receipt = run_experiment(experiment)

    assert receipt.verdict.outcome == VERDICT_PASS
    assert receipt.session_ids == (seen["session"],)
    assert seen["db"].startswith(seen["home"])
    assert not Path(seen["home"]).exists()


def test_receipts_are_sealed_private_and_reject_duplicates(tmp_path: Path) -> None:
    experiment = Experiment(
        "receipt_probe",
        "seals one receipt",
        Effect("noop_effect", "does nothing", _noop_effect_apply),
        Safety(),
        _quiet_oracle(),
        lambda _envelope, _case, _detail: {},
    )
    receipt = run_experiment(experiment)

    path = write_chaos_receipt(tmp_path, receipt)

    assert stat.S_IMODE(path.stat().st_mode) == 0o600
    projected = project_chaos_receipt(json.loads(path.read_text(encoding="utf-8")))
    assert projected is not None
    assert projected["experiment"] == "receipt_probe"
    assert project_chaos_receipt({"schema": "other"}) is None


def test_resolve_and_summarize_experiments() -> None:
    assert resolve_experiments(None) == (STAFFING_WINDOW, RUNNER_HARD_KILL)
    assert resolve_experiments([RUNNER_HARD_KILL.name]) == (RUNNER_HARD_KILL,)
    with pytest.raises(ValueError, match="unknown chaos experiment"):
        resolve_experiments(["network_partition"])
    with pytest.raises(ValueError, match="non-empty"):
        resolve_experiments([])

    report = {
        "schema": CHAOS_REPORT_SCHEMA,
        "experiments": {
            "staffing_window": {
                "verdict": VERDICT_PASS,
                "reason_codes": [],
                "receipt_path": "/private/a",
            },
            "runner_hard_kill": {
                "verdict": VERDICT_FAIL,
                "reason_codes": ["orphan_not_reclaimed"],
                "receipt_path": "/private/b",
            },
        },
    }
    summary = chaos_report_summary(report)
    assert summary["schema"] == CHAOS_SUMMARY_SCHEMA
    assert summary["passed"] is False
    assert summary["failed"] == ["runner_hard_kill"]
    assert summary["reason_codes"]["runner_hard_kill"] == ["orphan_not_reclaimed"]
    # Experiments are summarized in name order, so receipts follow the same order.
    assert summary["receipts"] == ["/private/b", "/private/a"]
    with pytest.raises(ValueError, match="schema"):
        chaos_report_summary({"schema": "nope", "experiments": {}})


def test_cli_prints_verdicts_and_exits_on_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[Any, ...] | None] = []

    def _fake_run(names: Any = None, **_kwargs: Any) -> dict[str, Any]:
        calls.append(names)
        return {
            "schema": CHAOS_REPORT_SCHEMA,
            "receipt_root": "/private/chaos",
            "experiments": {
                "staffing_window": {
                    "verdict": VERDICT_FAIL,
                    "reason_codes": ["staffing_receipt_missing"],
                    "gap_notes": ["documented gap"],
                    "receipt_path": "/private/chaos/x/receipt.json",
                }
            },
            "passed": False,
        }

    monkeypatch.setattr(chaos_runner, "run_chaos_experiments", _fake_run)
    text = io.StringIO()
    with redirect_stdout(text):
        code = run_chaos_cli(SimpleNamespace(experiment=["staffing_window"], json=False))
    assert code == 1
    assert calls == [("staffing_window",)]
    assert "staffing_window: fail (staffing_receipt_missing)" in text.getvalue()
    assert "gap: documented gap" in text.getvalue()

    payload = io.StringIO()
    with redirect_stdout(payload):
        assert run_chaos_cli(SimpleNamespace(experiment=None, json=True)) == 1
    assert json.loads(payload.getvalue())["passed"] is False
    assert calls[-1] is None


def test_safety_contract_rejects_malformed_bounds() -> None:
    with pytest.raises(ValueError, match="session prefix"):
        Safety(session_prefix="live")
    with pytest.raises(ValueError, match="gate variable"):
        Safety(gate_variable="CHAOS")
    assert chaos_safety.live_database_paths({})  # the default store path is always refused
