"""Regression coverage for checks that must survive ``python -O``."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from agency_runtime.core import canary


def _assessment() -> canary._ReadinessAssessment:
    return canary._ReadinessAssessment(
        native={},
        control={"enabled": True},
        profile_scope="isolated-profile",
        platform={"system": "test", "release": "test", "machine": "test"},
        unmet=(),
    )


def _run_with(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    preparation: canary._LivePreparation,
    outcome: canary._InvocationOutcome | None = None,
) -> dict[str, object]:
    assessment = _assessment()
    monkeypatch.setattr(canary, "_assess_readiness", lambda *_args, **_kwargs: assessment)
    monkeypatch.setattr(canary, "_prepare_live_invocation", lambda *_args, **_kwargs: preparation)
    if outcome is not None:
        monkeypatch.setattr(
            canary,
            "_invoke_and_collect_evidence",
            lambda *_args, **_kwargs: outcome,
        )
    return canary.run_canary(
        "codex",
        execute=True,
        confirm="RUN LIVE codex CANARY",
        db_path=tmp_path / "agency.db",
    )


@pytest.mark.parametrize(
    ("prompt", "query_hash"),
    [(None, "hash"), ("prompt", None)],
)
def test_canary_rejects_incomplete_preparation_without_assert(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    prompt: str | None,
    query_hash: str | None,
) -> None:
    report = _run_with(
        monkeypatch,
        tmp_path,
        canary._LivePreparation(
            store=object(),
            before={},
            backend=object(),
            prompt=prompt,
            expected_query_hash=query_hash,
        ),
    )

    assert report["canary_passed"] is False
    assert report["unmet_prerequisites"] == [
        "safe canary preparation returned incomplete invocation state"
    ]


@pytest.mark.parametrize(
    ("result", "evidence"),
    [(None, {}), ({}, None)],
)
def test_canary_rejects_incomplete_outcome_without_assert(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    result: dict[str, object] | None,
    evidence: dict[str, object] | None,
) -> None:
    report = _run_with(
        monkeypatch,
        tmp_path,
        canary._LivePreparation(
            store=object(),
            before={},
            backend=object(),
            prompt="prompt",
            expected_query_hash="hash",
        ),
        canary._InvocationOutcome(result=result, evidence=evidence),
    )

    assert report["live_attempted"] is True
    assert report["unmet_prerequisites"] == [
        "safe host invocation returned incomplete evidence state"
    ]


def test_canary_rejects_missing_attestation_store_without_assert(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(
        canary,
        "_evaluate_proof",
        lambda *_args, **_kwargs: canary._CanaryProof(
            invocation={},
            result_scope="isolated-profile",
            passed=True,
            failures=(),
        ),
    )
    monkeypatch.setattr(canary, "_attestation_identity_is_current", lambda *_args: True)
    report = _run_with(
        monkeypatch,
        tmp_path,
        canary._LivePreparation(
            store=None,
            before={},
            backend=object(),
            prompt="prompt",
            expected_query_hash="hash",
        ),
        canary._InvocationOutcome(result={}, evidence={}),
    )

    assert report["attestation_persisted"] is False
    assert report["unmet_prerequisites"] == ["canary attestation store is unavailable"]


@pytest.mark.parametrize(
    ("backend", "store", "before"),
    [(None, object(), {}), (object(), None, {}), (object(), object(), None)],
)
def test_canary_invocation_rejects_incomplete_prerequisites_without_assert(
    backend: object | None,
    store: object | None,
    before: dict[str, object] | None,
    tmp_path: Path,
) -> None:
    outcome = canary._invoke_and_collect_evidence(
        canary._LivePreparation(
            store=store,
            before=before,
            backend=backend,
            prompt="prompt",
            expected_query_hash="hash",
        ),
        host="codex",
        path=tmp_path / "agency.db",
        prompt="prompt",
        expected_query_hash="hash",
    )

    assert outcome.error == "safe canary invocation prerequisites are incomplete"
    assert outcome.result is None
    assert outcome.evidence is None


def test_production_package_contains_no_optimization_sensitive_asserts() -> None:
    repository = Path(__file__).parents[1]
    production_roots = (repository / "agency_runtime", repository / "scripts")
    assertions = [
        (path.relative_to(repository), node.lineno)
        for root in production_roots
        for path in root.rglob("*.py")
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"), filename=str(path)))
        if isinstance(node, ast.Assert)
    ]

    assert assertions == []
