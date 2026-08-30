"""Outcome-comparison evaluation remains bounded and evidence-honest."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from agency_runtime.core.bounded_io import FileSizeLimitError
from agency_runtime.core.evals import comparative as subject
from agency_runtime.core.evals.comparative import (
    MIN_LIVE_PAIRS_FOR_DIRECTIONAL_CLAIM,
    ComparativeObservation,
    evaluate_comparative_outcomes,
    load_comparative_jsonl,
)


def _observation(
    *,
    scenario: str = "scenario",
    trial: str = "trial",
    run: str = "run",
    mode: str = "native_only",
    evidence: str = "live_host",
    quality: float = 0.7,
    defects: int = 1,
    duration: float = 100.0,
    cost: float = 0.2,
    delegated: int = 0,
) -> dict[str, object]:
    return {
        "schema_version": 1,
        "scenario_id": scenario,
        "trial_id": trial,
        "run_id": run,
        "host": "codex",
        "mode": mode,
        "evidence_kind": evidence,
        "blinded_label": f"blind-{run}",
        "completed": True,
        "quality_score": quality,
        "tests_total": 10,
        "tests_failed": 0,
        "escaped_defects": defects,
        "duration_ms": duration,
        "cost_usd": cost,
        "retries": 0,
        "duplicate_work": 0,
        "merge_conflicts": 0,
        "synthesis_failures": 0,
        "supervisor_interventions": 0,
        "delegated_units": delegated,
        "requested_model": "task-general",
        "actual_model": "provider/model",
        "router": "",
    }


def test_observation_schema_is_strict_and_content_free() -> None:
    parsed = ComparativeObservation.from_mapping(_observation())
    assert parsed.mode == "native_only"
    assert parsed.public_dict()["schema_version"] == 1

    for field, value in (
        ("completed", 1),
        ("quality_score", float("nan")),
        ("tests_failed", 11),
        ("mode", "invented"),
        ("evidence_kind", "claimed_live"),
    ):
        raw = _observation()
        raw[field] = value
        with pytest.raises(ValueError):
            ComparativeObservation.from_mapping(raw)

    with pytest.raises(ValueError, match="unsupported fields"):
        ComparativeObservation.from_mapping({**_observation(), "prompt": "secret content"})


def test_simulated_pairs_never_support_directional_claim() -> None:
    report = evaluate_comparative_outcomes(
        [
            _observation(evidence="simulated"),
            _observation(
                run="agency",
                mode="agency_prefer",
                evidence="simulated",
                quality=0.9,
                defects=0,
                delegated=2,
            ),
        ]
    )

    mode = report["modes"]["agency_prefer"]
    assert mode["all_evidence"]["pair_count"] == 1
    assert mode["live_host"]["pair_count"] == 0
    assert mode["directional_claim_eligible"] is False
    assert report["superiority_claimed"] is False


def test_live_gate_requires_controlled_model_matched_pairs() -> None:
    rows: list[dict[str, object]] = []
    for index in range(MIN_LIVE_PAIRS_FOR_DIRECTIONAL_CLAIM):
        scenario = f"scenario-{index}"
        trial = f"trial-{index}"
        rows.extend(
            [
                _observation(scenario=scenario, trial=trial, run=f"native-{index}"),
                _observation(
                    scenario=scenario,
                    trial=trial,
                    run=f"agency-{index}",
                    mode="agency_prefer",
                    quality=0.8,
                    defects=0,
                    delegated=2,
                ),
            ]
        )

    report = evaluate_comparative_outcomes(rows)
    preferred = report["modes"]["agency_prefer"]
    assert preferred["live_host"]["pair_count"] == MIN_LIVE_PAIRS_FOR_DIRECTIONAL_CLAIM
    assert preferred["live_host"]["blinded_pair_count"] == MIN_LIVE_PAIRS_FOR_DIRECTIONAL_CLAIM
    assert preferred["live_host"]["quality_score_delta"] == pytest.approx(0.1)
    assert preferred["live_host"]["escaped_defects_delta"] == -1
    assert preferred["directional_claim_eligible"] is True
    assert report["superiority_claimed"] is False

    rows[-1]["actual_model"] = "different/provider-model"
    mismatched = evaluate_comparative_outcomes(rows)["modes"]["agency_prefer"]
    assert mismatched["directional_claim_eligible"] is False
    assert mismatched["live_model_mismatch_count"] == 1

    rows[-1]["actual_model"] = "provider/model"
    rows[-1]["router"] = "different-router"
    router_mismatch = evaluate_comparative_outcomes(rows)["modes"]["agency_prefer"]
    assert router_mismatch["directional_claim_eligible"] is False
    assert router_mismatch["live_route_identity_mismatch_count"] == 1

    rows[-1]["router"] = ""
    rows[-1]["blinded_label"] = rows[-2]["blinded_label"]
    unblinded = evaluate_comparative_outcomes(rows)["modes"]["agency_prefer"]
    assert unblinded["directional_claim_eligible"] is False
    assert unblinded["live_host"]["blinded_pair_count"] == (
        MIN_LIVE_PAIRS_FOR_DIRECTIONAL_CLAIM - 1
    )


def test_delegation_regret_and_duplicate_trials_are_visible() -> None:
    rows = [
        _observation(quality=0.8, defects=0),
        _observation(
            run="agency",
            mode="agency_strong",
            quality=0.8,
            defects=0,
            duration=150.0,
            cost=0.4,
            delegated=2,
        ),
    ]
    strong = evaluate_comparative_outcomes(rows)["modes"]["agency_strong"]["live_host"]
    assert strong["delegation_regret_count"] == 1
    assert strong["delegation_regret_rate"] == 1.0

    with pytest.raises(ValueError, match="duplicate"):
        evaluate_comparative_outcomes([rows[0], rows[0]])
    with pytest.raises(ValueError, match="duplicate run id"):
        evaluate_comparative_outcomes([rows[0], {**rows[1], "run_id": rows[0]["run_id"]}])


def test_jsonl_loader_is_bounded_and_reports_line_errors(tmp_path: Path) -> None:
    path = tmp_path / "comparative.jsonl"
    path.write_text(
        "\n".join(
            json.dumps(row)
            for row in (
                _observation(),
                _observation(run="agency", mode="agency_observe"),
            )
        ),
        encoding="utf-8",
    )
    assert len(load_comparative_jsonl(path)) == 2

    path.write_text("{}\n", encoding="utf-8")
    with pytest.raises(ValueError, match="line 1"):
        load_comparative_jsonl(path)

    path.write_text("\n", encoding="utf-8")
    with pytest.raises(ValueError, match="empty"):
        load_comparative_jsonl(path)


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("scenario_id", "", "1..128"),
        ("scenario_id", "bad\x7fvalue", "control characters"),
        ("tests_total", True, "must be an integer"),
        ("tests_total", -1, "between 0"),
        ("quality_score", True, "must be a number"),
        ("schema_version", 2, "unsupported comparative observation"),
    ],
)
def test_observation_primitive_validation_boundaries(
    field: str,
    value: object,
    message: str,
) -> None:
    raw = _observation()
    raw[field] = value

    with pytest.raises(ValueError, match=message):
        ComparativeObservation.from_mapping(raw)


def test_jsonl_loader_rejects_size_encoding_count_and_shape_boundaries(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = tmp_path / "comparative.jsonl"
    monkeypatch.setattr(
        subject,
        "read_bounded_regular_file",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(FileSizeLimitError("large")),
    )
    with pytest.raises(ValueError, match="4 MiB"):
        load_comparative_jsonl(path)

    monkeypatch.setattr(subject, "read_bounded_regular_file", lambda *_args, **_kwargs: b"\xff")
    with pytest.raises(ValueError, match="UTF-8"):
        load_comparative_jsonl(path)

    monkeypatch.setattr(
        subject,
        "read_bounded_regular_file",
        lambda *_args, **_kwargs: b"{not-json}\n",
    )
    with pytest.raises(ValueError, match="line 1 is invalid JSON"):
        load_comparative_jsonl(path)

    monkeypatch.setattr(
        subject,
        "read_bounded_regular_file",
        lambda *_args, **_kwargs: b"[]\n",
    )
    with pytest.raises(ValueError, match="line 1 must be an object"):
        load_comparative_jsonl(path)

    monkeypatch.setattr(subject, "MAX_COMPARATIVE_OBSERVATIONS", 1)
    payload = "\n".join(
        json.dumps(row)
        for row in (
            _observation(),
            _observation(run="second", mode="agency_observe"),
        )
    ).encode()
    monkeypatch.setattr(
        subject,
        "read_bounded_regular_file",
        lambda *_args, **_kwargs: payload,
    )
    with pytest.raises(ValueError, match="observation limit"):
        load_comparative_jsonl(path)


def test_evaluator_rejects_empty_and_bounded_inputs_and_skips_unpaired_modes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with pytest.raises(ValueError, match="requires observations"):
        evaluate_comparative_outcomes([])

    monkeypatch.setattr(subject, "MAX_COMPARATIVE_OBSERVATIONS", 1)
    with pytest.raises(ValueError, match="observation limit"):
        evaluate_comparative_outcomes(
            [
                _observation(),
                _observation(run="second", mode="agency_observe"),
            ]
        )
    monkeypatch.setattr(subject, "MAX_COMPARATIVE_OBSERVATIONS", 4096)

    report = evaluate_comparative_outcomes(
        [
            _observation(
                run="orphan",
                mode="agency_observe",
            ),
            _observation(
                scenario="mismatch",
                trial="mismatch",
                run="baseline-mismatch",
                evidence="simulated",
            ),
            _observation(
                scenario="mismatch",
                trial="mismatch",
                run="candidate-mismatch",
                mode="agency_prefer",
                evidence="contract_only",
            ),
        ]
    )
    assert report["modes"]["agency_observe"]["all_evidence"]["pair_count"] == 0
    assert report["modes"]["agency_prefer"]["all_evidence"]["pair_count"] == 0
