from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from agency_runtime.core.codex_native_plan_scope import (
    deserialize_codex_native_plan_scope,
)
from agency_runtime.core.config import reset_config_cache
from agency_runtime.core.evals.product_host import (
    _expected_prompt_hash,
    _prompt_with_workspace_write_proof,
)
from agency_runtime.core.evals.product_scenarios import product_scenario
from agency_runtime.core.host_capabilities import native_adapter_capability_receipt
from agency_runtime.core.preflight import run_preflight
from agency_runtime.core.preflight_failure import PreflightInvariantError
from agency_runtime.core.store.sqlite import Store
from agency_runtime.core.structured_provider import StructuredProviderResult
from tests.runtime_support import write_provider_config

_OUTCOMES = (
    (
        "unit-discovery",
        "Map the bounded Python CLI product request and its requested artifacts.",
        "analysis",
        "software-engineering",
        "analysis",
        (),
        "codebase-onboarding-engineer",
    ),
    (
        "unit-product",
        "Implement the requested Python CLI product artifacts.",
        "implementation-change",
        "software-engineering",
        "implementation",
        ("unit-discovery",),
        "python-application-engineer",
    ),
    (
        "unit-tests",
        "Implement meaningful tests for the requested Python CLI product.",
        "test-code",
        "quality-assurance",
        "testing",
        ("unit-product",),
        "test-automation-engineer",
    ),
    (
        "unit-review",
        "Review the complete bounded product for correctness.",
        "review-report",
        "software-engineering",
        "review",
        ("unit-tests",),
        "code-reviewer",
    ),
    (
        "unit-evidence",
        "Run the requested tests and retain bounded verification evidence.",
        "test-evidence",
        "quality-assurance",
        "testing",
        ("unit-tests", "unit-review"),
        "test-results-analyzer",
    ),
)


@pytest.fixture()
def configured_store(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    config_path = tmp_path / "agency.yaml"
    write_provider_config(config_path)
    monkeypatch.setenv("AGENCY_CONFIG_PATH", str(config_path))
    reset_config_cache()
    try:
        yield Store(tmp_path / "agency.db", config_path=config_path)
    finally:
        reset_config_cache()


def _accepted_product_provider(_provider, _prompt, schema, **_kwargs):
    properties = schema.get("properties", {})
    value = (
        {
            "request_summary": "A bounded Python CLI implementation and assurance plan.",
            "units": [
                {
                    "unit_id": unit_id,
                    "outcome": outcome,
                    "artifact_kind": artifact_kind,
                    "domains": [domain],
                    "stacks": ["python"] if artifact_kind == "implementation-change" else [],
                    "capability_ids": [capability],
                    "novel_capability": "",
                    "depends_on": list(depends_on),
                }
                for (
                    unit_id,
                    outcome,
                    artifact_kind,
                    domain,
                    capability,
                    depends_on,
                    _specialist,
                ) in _OUTCOMES
            ],
        }
        if "request_summary" in properties
        else {
            "units": [
                {
                    "unit_id": unit_id,
                    "decision": "staff",
                    "ranked_semantic": [
                        {
                            "agent_id": specialist,
                            "score": 0.99,
                            "classification": "required",
                            "positive_evidence": ["scope-match"],
                            "negative_evidence": [],
                        }
                    ],
                }
                for unit_id, *_rest, specialist in _OUTCOMES
            ]
        }
    )
    return StructuredProviderResult(
        value=value,
        provider_name="task-agency-router",
        provider_type="litellm",
        transport="",
        requested_model="router-alias",
        model_group="router-alias",
        actual_model="gpt-5.6-mini",
        model_receipt_source="response.body.model",
        latency_ms=17,
    )


def _executed_product_prompt(trial_id: str) -> str:
    prompt = product_scenario("python-cli-service").prompt(trial_id=trial_id)
    executed, _token = _prompt_with_workspace_write_proof(
        prompt,
        _expected_prompt_hash(prompt),
    )
    return executed


def _capabilities(session_id: str, trace_id: str):
    return native_adapter_capability_receipt(
        "codex",
        platform="windows" if os.name == "nt" else "linux",
        session_id=session_id,
        trace_id=trace_id,
    )


def test_legacy_product_separator_fails_atomically_with_bounded_invariant(
    configured_store: Store,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from agency_runtime.core.workforce import inference

    monkeypatch.setattr(
        inference,
        "invoke_structured_provider_result",
        _accepted_product_provider,
    )
    session_id = "ar214-failing-session"
    trace_id = "ar214-failing-trace"
    prompt = _executed_product_prompt("ar214-failing-fixture").replace(
        "`python-cli-service`, trial",
        "`python-cli-service` / trial",
        1,
    )

    with pytest.raises(PreflightInvariantError):
        run_preflight(
            configured_store,
            session_id=session_id,
            trace_id=trace_id,
            user_message=prompt,
            host="codex",
            capability_receipt=_capabilities(session_id, trace_id),
        )

    receipt = configured_store.get_preflight_failure_receipt(session_id, trace_id)
    assert receipt is not None
    assert receipt["stage"] == "context_delivery"
    assert receipt["reason_code"] == "context_delivery_failed"
    assert receipt["exception_category"] == "validation_error"
    assert receipt["invariant_code"] == "native_plan_scope_invalid"
    assert receipt["provider_attempts"]
    counts = configured_store.runtime_table_counts()
    assert counts["routing_decisions"] == 0
    assert counts["codex_native_plan_scopes"] == 0
    assert counts["specialists_loaded"] == 0
    assert counts["delegation_events"] == 0
    connection = configured_store._connect()
    try:
        durable = dict(
            connection.execute(
                "SELECT * FROM preflight_failure_receipts WHERE trace_id = ?",
                (trace_id,),
            ).fetchone()
        )
    finally:
        connection.close()
    durable_text = json.dumps(durable, sort_keys=True)
    for forbidden in (
        "python-cli-service",
        "app.py",
        "tests/test_app.py",
        ".agency-runtime-workspace-write-proof",
        "preflight invariant failed",
    ):
        assert forbidden not in durable_text


def test_product_prompt_preserves_exact_paths_through_ready_commit(
    configured_store: Store,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from agency_runtime.core.workforce import inference

    monkeypatch.setattr(
        inference,
        "invoke_structured_provider_result",
        _accepted_product_provider,
    )
    session_id = "ar214-repaired-session"
    trace_id = "ar214-repaired-trace"
    result = run_preflight(
        configured_store,
        session_id=session_id,
        trace_id=trace_id,
        user_message=_executed_product_prompt("ar214-repaired-fixture"),
        host="codex",
        capability_receipt=_capabilities(session_id, trace_id),
    )

    assert len(result.delegation_plan) == len(_OUTCOMES)
    implementation = next(
        row
        for row in result.delegation_plan
        if row["recommended_agent"] == "python-application-engineer"
    )
    connection = configured_store._connect()
    try:
        row = connection.execute(
            "SELECT scope_payload FROM codex_native_plan_scopes "
            "WHERE trace_id = ? AND work_unit_id = ?",
            (trace_id, implementation["work_unit_id"]),
        ).fetchone()
    finally:
        connection.close()
    scope = deserialize_codex_native_plan_scope(row["scope_payload"])
    assert scope.mutation_scope.mode == "workspace_write"
    assert scope.mutation_scope.path_prefixes == (
        ".agency-runtime-workspace-write-proof",
        "README",
        "README.md",
        "app.py",
        "tests/test_app.py",
    )
    assert "/" not in scope.mutation_scope.path_prefixes
    assert "." not in scope.mutation_scope.path_prefixes
    assert not any("`" in item for item in scope.mutation_scope.path_prefixes)
    counts = configured_store.runtime_table_counts()
    assert counts["routing_decisions"] == 1
    assert counts["codex_native_plan_scopes"] == len(_OUTCOMES)


def test_schema_v42_adds_empty_invariant_to_existing_failure_receipts(tmp_path: Path) -> None:
    path = tmp_path / "agency.db"
    store = Store(path)
    started = store.begin_preflight_attempt(
        session_id="migration-session",
        trace_id="migration-trace",
        request_fingerprint="a" * 64,
        request_kind="nontrivial",
        host="codex",
    )
    assert store.fail_preflight_attempt(
        session_id="migration-session",
        trace_id="migration-trace",
        attempt_token=started["attempt_token"],
    )
    connection = store._connect()
    try:
        connection.execute(
            "ALTER TABLE preflight_failure_receipts DROP COLUMN invariant_code"
        )
        connection.execute("DELETE FROM schema_version")
        connection.execute("INSERT INTO schema_version (version) VALUES (41)")
        connection.commit()
    finally:
        connection.close()

    migrated = Store(path)
    receipt = migrated.get_preflight_failure_receipt(
        "migration-session",
        "migration-trace",
    )

    assert receipt is not None
    assert receipt["schema_version"] == "agency.preflight.failure.v3"
    assert receipt["invariant_code"] == ""
