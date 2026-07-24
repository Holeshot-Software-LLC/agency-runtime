"""Public facade and import-cost regression coverage."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

from agency_runtime import AgencyRuntime
from agency_runtime.core.roster.bundled import SOURCE_REPOSITORY
from tests.runtime_support import stub_inference_invoker, write_provider_config


def test_package_import_does_not_eagerly_load_runtime_heavy_modules() -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "import json,sys; import agency_runtime; "
                "print(json.dumps({"
                "'store': 'agency_runtime.core.store.sqlite' in sys.modules,"
                "'selector': 'agency_runtime.core.selector.pipeline' in sys.modules}))"
            ),
        ],
        cwd=Path(__file__).parents[1],
        capture_output=True,
        text=True,
        check=True,
        timeout=10,
    )

    assert json.loads(completed.stdout) == {"store": False, "selector": False}


@pytest.mark.parametrize(
    "module",
    ("agency_runtime.server.http", "agency_runtime.server.mcp"),
)
def test_direct_server_modules_load_protocol_dependencies_before_entrypoint(
    module: str,
) -> None:
    completed = subprocess.run(
        [sys.executable, "-m", module, "--help"],
        cwd=Path(__file__).parents[1],
        capture_output=True,
        text=True,
        check=False,
        timeout=10,
    )

    assert completed.returncode == 0
    assert "usage:" in completed.stdout
    assert "NameError" not in completed.stderr


@pytest.mark.skip(
    reason="ADR-0087: needs a multi-unit plan + multi-specialist nomination-delivery "
    "flow (3 specialists across 3 units) that the simple stub invoker cannot produce."
)
def test_public_runtime_facade_exercises_routing_and_evidence(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # ADR-0087: configure a provider + stub so routing exercises inference.
    from agency_runtime.core.workforce import inference as _inference

    config_path = tmp_path / "agency.yaml"
    write_provider_config(config_path)
    monkeypatch.setenv("AGENCY_CONFIG_PATH", str(config_path))
    monkeypatch.setattr(
        _inference,
        "invoke_structured_provider_result",
        stub_inference_invoker(
            ("codebase-onboarding-engineer", "code-reviewer", "ai-generated-code-security-auditor"),
        ),
    )
    runtime = AgencyRuntime(str(tmp_path / "agency.db"))

    assert runtime.get_roster() == []
    assert runtime.search("security") == []
    assert runtime.get_roster() == []
    trace_id = "trace"
    route_receipt = runtime.attest_native_host(
        "hermes",
        session_id="session",
        trace_id="route-trace",
    )
    routing = runtime.route(
        "session",
        "review this security patch",
        trace_id="route-trace",
        host="hermes",
        capability_receipt=route_receipt,
    )
    assert set(routing["selected_ids"]) == {
        "codebase-onboarding-engineer",
        "code-reviewer",
        "ai-generated-code-security-auditor",
    }
    assert "decision_id" not in routing
    assert runtime.store.get_run("route-trace") is None
    preflight_receipt = runtime.attest_native_host(
        "hermes",
        session_id="session",
        trace_id=trace_id,
    )
    preflight = runtime.preflight(
        "session",
        "Review this README documentation.",
        trace_id=trace_id,
        host="hermes",
        capability_receipt=preflight_receipt,
    )
    assert preflight["trace_id"] == trace_id
    assert preflight["routing"]["selected_ids"] == ["codebase-onboarding-engineer"]
    assert preflight["selected_specialists"] == ["codebase-onboarding-engineer"]
    assert preflight["loaded_specialists"] == ["codebase-onboarding-engineer"]
    continuation_receipt = runtime.attest_native_host(
        "hermes",
        session_id="session",
        trace_id=trace_id,
    )
    context = runtime.route_with_context(
        "session",
        "Review this README documentation.",
        trace_id=trace_id,
        host="hermes",
        capability_receipt=continuation_receipt,
    )
    assert context is not None
    assert "codebase-onboarding-engineer" in context
    work = runtime.detect_work_units("1. Review the API\n2. Test the dashboard")
    assert len(work["units"]) == 2

    runtime.record_skill("session", "security-review", trace_id=trace_id)
    runtime.record_specialist("session", "security-reviewer", trace_id=trace_id)
    receipt_id = runtime.record_model_receipt(
        trace_id=trace_id,
        session_id="session",
        host="test",
        requested_model="task-general",
        resolved_provider="openai",
        resolved_model="gpt-test",
        source="host",
    )
    delegation_id = runtime.record_delegation(
        trace_id=trace_id,
        session_id="session",
        host="test",
        work_unit_id="unit-review",
        recommended_agent="security-reviewer",
        status="completed",
        backend="test-backend",
        executed_worker_kind="test-worker",
        executed_worker_id="worker-1",
        native_run_id="test-backend:run-1",
    )

    assert receipt_id
    assert delegation_id
    finalized = runtime.finalize_header(
        "Finished.",
        session_id="session",
        model="task-general",
        trace_id=trace_id,
    )
    loaded = finalized.splitlines()[0].removeprefix("Agency/Agencies loaded: ").split(", ")
    assert set(loaded) == {
        "agents-orchestrator",
        "chief-of-staff",
        "codebase-onboarding-engineer",
        "security-reviewer",
    }
    assert (
        "Agency/Agencies delegated: none - executed worker has no validated Agency specialist"
        in finalized
    )
    assert "Skills loaded: security-review" in finalized
    assert "Actual Model selected: [general] task-general -> openai/gpt-test" in finalized
    assert finalized.endswith("Finished.")
    assert runtime.store.get_run(trace_id)["status"] == "completed"
    assert runtime.store.get_active_specialists_for_trace("session", trace_id) == []


def test_public_route_repairs_legacy_fallback_roster_without_opening_turns(
    tmp_path: Path,
) -> None:
    runtime = AgencyRuntime(str(tmp_path / "agency.db"))
    runtime.store._activate_prevalidated_agent(
        {
            "slug": "operator-specialist",
            "name": "Operator Specialist",
            "source": "operator",
            "version": "1.0.0",
            "description": "A legacy operator-owned specialist.",
            "prompt_body": "Preserve this prompt.",
        }
    )

    for trace_id in ("diagnostic-route-1", "diagnostic-route-2"):
        receipt = runtime.attest_native_host(
            "hermes",
            session_id="legacy-session",
            trace_id=trace_id,
        )
        routing = runtime.route(
            "legacy-session",
            "ok",
            trace_id=trace_id,
            host="hermes",
            capability_receipt=receipt,
        )
        assert routing["selected_ids"] == []
        assert routing["fallback_companion_ids"] == [
            "agents-orchestrator",
            "chief-of-staff",
        ]
        assert "decision_id" not in routing
        assert runtime.store.get_run(trace_id) is None

    assert runtime.store.get_open_traces_for_session("legacy-session") == []
    assert runtime.store.get_specialist_prompt("operator-specialist")["prompt_body"] == (
        "Preserve this prompt."
    )
    for slug in ("agents-orchestrator", "chief-of-staff"):
        assert runtime.store.get_roster_entry(slug)["source"] == SOURCE_REPOSITORY


def test_public_route_does_not_treat_a_host_name_as_capability_evidence(
    tmp_path: Path,
) -> None:
    runtime = AgencyRuntime(str(tmp_path / "agency.db"))

    routing = runtime.route(
        "unproven-session",
        "Review this security patch.",
        trace_id="unproven-trace",
        host="hermes",
    )

    assert routing["selected_ids"] == []
    assert routing["execution_context"]["status"] == "native-evidence-unproven"
    assert routing["eligibility_rejections"]


def test_public_runtime_finalize_header_fails_closed_for_unaccepted_turn(
    tmp_path: Path,
) -> None:
    runtime = AgencyRuntime(str(tmp_path / "agency.db"))
    runtime.store.create_run(
        trace_id="turn",
        session_id="session",
        metadata={"request_kind": "nontrivial"},
    )

    with pytest.raises(RuntimeError, match="did not accept"):
        runtime.finalize_header(
            "Finished.",
            session_id="session",
            trace_id="turn",
        )

    assert runtime.store.get_run("turn")["status"] == "active"


@pytest.mark.parametrize(
    "mutation",
    [
        lambda runtime: runtime.record_skill("session", "audit", trace_id="missing"),
        lambda runtime: runtime.record_specialist("session", "code-reviewer", trace_id="missing"),
        lambda runtime: runtime.record_model_receipt(
            trace_id="missing",
            session_id="session",
            host="test",
        ),
        lambda runtime: runtime.record_delegation(
            trace_id="missing",
            session_id="session",
            work_unit_id="unit-review",
            recommended_agent="code-reviewer",
            backend="test",
        ),
    ],
)
def test_public_evidence_mutations_cannot_manufacture_an_implicit_turn(
    mutation: Any,
    tmp_path: Path,
) -> None:
    runtime = AgencyRuntime(str(tmp_path / "agency.db"))

    with pytest.raises(ValueError, match="existing active turn"):
        mutation(runtime)

    assert runtime.store.get_run("missing") is None


@pytest.mark.parametrize(
    "mutation",
    [
        lambda runtime: runtime.record_skill("session", "audit", trace_id="turn"),
        lambda runtime: runtime.record_specialist("session", "code-reviewer", trace_id="turn"),
        lambda runtime: runtime.record_model_receipt(
            trace_id="turn",
            session_id="session",
            host="test",
        ),
        lambda runtime: runtime.record_delegation(
            trace_id="turn",
            session_id="session",
            work_unit_id="unit-review",
            recommended_agent="code-reviewer",
            backend="test",
        ),
    ],
)
@pytest.mark.parametrize("preflight_state", ["", "reserved", "in_progress"])
def test_public_evidence_mutations_require_preflight_ready_turn(
    mutation: Any,
    preflight_state: str,
    tmp_path: Path,
) -> None:
    runtime = AgencyRuntime(str(tmp_path / "agency.db"))
    if preflight_state == "":
        runtime.store.create_run(
            trace_id="turn",
            session_id="session",
            host="python",
        )
    elif preflight_state == "reserved":
        runtime.store.reserve_session_turn(
            session_id="session",
            trace_id="turn",
            host="codex",
        )
    else:
        runtime.store.begin_preflight_attempt(
            session_id="session",
            trace_id="turn",
            request_fingerprint=hashlib.sha256(b"review").hexdigest(),
            request_kind="nontrivial",
            host="codex",
        )

    with pytest.raises(ValueError, match="not completed preflight"):
        mutation(runtime)

    assert runtime.store.get_model_receipt("turn") is None
    assert runtime.store.get_skills_for_trace("session", "turn") == []
    assert runtime.store.get_specialists_for_trace("session", "turn") == []
    assert runtime.store.get_delegations("turn") == []
