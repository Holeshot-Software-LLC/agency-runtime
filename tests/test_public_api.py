"""Public facade and import-cost regression coverage."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from agency_runtime import AgencyRuntime


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


def test_public_runtime_facade_exercises_routing_and_evidence(tmp_path: Path) -> None:
    runtime = AgencyRuntime(str(tmp_path / "agency.db"))

    assert runtime.get_roster() == []
    assert runtime.search("security") == []
    assert runtime.route("session", "review this security patch")["selected_ids"] == []
    context = runtime.route_with_context("session", "review this security patch")
    assert context is not None
    assert "status=no_catalog" in context
    work = runtime.detect_work_units("1. Review the API\n2. Test the dashboard")
    assert len(work["units"]) == 2

    runtime.record_skill("session", "security-review")
    runtime.record_specialist("session", "security-reviewer")
    receipt_id = runtime.record_model_receipt(
        trace_id="trace-model",
        session_id="session",
        host="test",
        requested_model="task-general",
        resolved_provider="openai",
        resolved_model="gpt-test",
        source="host",
    )
    delegation_id = runtime.record_delegation(
        trace_id="trace-delegation",
        session_id="session",
        host="test",
        recommended_agent="security-reviewer",
        status="completed",
        backend="test-backend",
    )

    assert receipt_id
    assert delegation_id
    finalized = runtime.finalize_header("Finished.", session_id="session", model="task-general")
    assert finalized.startswith("Agency/Agencies loaded: security-reviewer")
    assert "Agency/Agencies delegated: security-reviewer via test-backend" in finalized
    assert "Skills loaded: security-review" in finalized
    assert "Actual Model selected: [general] task-general -> openai/gpt-test" in finalized
    assert finalized.endswith("Finished.")
